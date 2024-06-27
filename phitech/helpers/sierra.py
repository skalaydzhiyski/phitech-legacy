from __future__ import annotations
import numpy as np
from numpy import datetime64, timedelta64
import pandas as pd
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from numpy import datetime64, timedelta64
from os import fstat
import struct
from struct import calcsize, Struct
from progiter import ProgIter

import os
from collections import defaultdict
from dataclasses import dataclass, field
import databento as db
from databento_dbn import FIXED_PRICE_SCALE, UNDEF_PRICE, BidAskPair
from sortedcontainers import SortedDict


@dataclass
class Order:
    id: int
    side: str
    price: int
    size: int
    ts_event: int
    is_tob: bool = field(default=False)


@dataclass
class LevelOrders:
    price: int
    orders: list[Order] = field(default_factory=list, compare=False)

    def __bool__(self) -> bool:
        return bool(self.orders)

    @property
    def level(self) -> PriceLevel:
        return PriceLevel(
            price=self.price,
            count=sum(1 for o in self.orders if not o.is_tob),
            size=sum(o.size for o in self.orders),
        )


@dataclass
class PriceLevel:
    price: int
    size: int = 0
    count: int = 0

    def __str__(self) -> str:
        price = self.price / FIXED_PRICE_SCALE
        return f"{self.size:4} @ {price:6.2f} | {self.count:2} order(s)"


@dataclass
class Book:
    orders_by_id: dict[int, Order] = field(default_factory=dict)
    offers: SortedDict[int, LevelOrders] = field(default_factory=SortedDict)
    bids: SortedDict[int, LevelOrders] = field(default_factory=SortedDict)

    def bbo(self) -> tuple[PriceLevel | None, PriceLevel | None]:
        return self.get_bid_level(), self.get_ask_level()

    def get_bid_level(self, idx: int = 0) -> PriceLevel | None:
        if self.bids and len(self.bids) > idx:
            # Reverse for bids to get highest prices first
            return self.bids.peekitem(-(idx + 1))[1].level
        return None

    def get_ask_level(self, idx: int = 0) -> PriceLevel | None:
        if self.offers and len(self.offers) > idx:
            return self.offers.peekitem(idx)[1].level
        return None

    def get_bid_level_by_px(self, px: int) -> PriceLevel | None:
        try:
            return self._get_level(px, "B").level
        except KeyError:
            return None

    def get_ask_level_by_px(self, px: int) -> PriceLevel | None:
        try:
            return self._get_level(px, "A").level
        except KeyError:
            return None

    def get_snapshot(self, level_count: int = 1) -> list[BidAskPair]:
        snapshots = []
        for level in range(level_count):
            ba_pair = BidAskPair()
            bid = self.get_bid_level(level)
            if bid:
                ba_pair.bid_px = bid.price
                ba_pair.bid_sz = bid.size
                ba_pair.bid_ct = bid.count
            ask = self.get_ask_level(level)
            if ask:
                ba_pair.ask_px = ask.price
                ba_pair.ask_sz = ask.size
                ba_pair.ask_ct = ask.count
            snapshots.append(ba_pair)
        return snapshots

    def apply(
        self,
        ts_event: int,
        action: str,
        side: str,
        order_id: int,
        price: int,
        size: int,
        flags: db.RecordFlags,
    ) -> None:
        # Trade or Fill: no change
        if action == "T" or action == "F":
            return
        # Clear book: remove all resting orders
        if action == "R":
            self._clear()
            return
        # side=N is only valid with Trade, Fill, and Clear actions
        assert side == "A" or side == "B"
        # UNDEF_PRICE indicates the book level should be removed
        if price == UNDEF_PRICE and flags & db.RecordFlags.F_TOB:
            self._side_levels(side).clear()
            return
        # Add: insert a new order
        if action == "A":
            self._add(ts_event, side, order_id, price, size, flags)
        # Cancel: partially or fully cancel some size from a resting order
        elif action == "C":
            self._cancel(side, order_id, price, size)
        # Modify: change the price and/or size of a resting order
        elif action == "M":
            self._modify(ts_event, side, order_id, price, size, flags)
        else:
            raise ValueError(f"Unknown {action =}")

    def _clear(self):
        self.orders_by_id.clear()
        self.offers.clear()
        self.bids.clear()

    def _add(
        self,
        ts_event: int,
        side: str,
        order_id: int,
        price: int,
        size: int,
        flags: db.RecordFlags,
    ):
        order = Order(
            order_id,
            side,
            price,
            size,
            ts_event,
            is_tob=bool(flags & db.RecordFlags.F_TOB),
        )
        if order.is_tob:
            levels = self._side_levels(side)
            levels.clear()
            levels[price] = LevelOrders(price=price, orders=[order])
        else:
            level = self._get_or_insert_level(price, side)
            assert order_id not in self.orders_by_id
            self.orders_by_id[order_id] = order
            level.orders.append(order)

    def _cancel(
        self,
        side: str,
        order_id: int,
        price: int,
        size: int,
    ):
        order = self.orders_by_id[order_id]
        level = self._get_level(price, side)
        assert order.size >= size
        order.size -= size
        # If the full size is cancelled, remove the order from the book
        if order.size == 0:
            self.orders_by_id.pop(order_id)
            level.orders.remove(order)
            # If the level is now empty, remove it from the book
            if not level:
                self._remove_level(price, side)

    def _modify(
        self,
        ts_event: int,
        side: str,
        order_id: int,
        price: int,
        size: int,
        flags: db.RecordFlags,
    ):

        order = self.orders_by_id.get(order_id)
        if order is None:
            # If order not found, treat it as an add
            self._add(ts_event, side, order_id, price, size, flags)
            return
        assert order.side == side, f"Order {order} changed side to {side}"
        prev_level = self._get_level(order.price, side)
        if order.price != price:
            prev_level.orders.remove(order)
            if not prev_level:
                self._remove_level(order.price, side)
            level = self._get_or_insert_level(price, side)
            level.orders.append(order)
        else:
            level = prev_level
        # The order loses its priority if the price changes or the size increases
        if order.price != price or order.size < size:
            order.ts_event = ts_event
            level.orders.remove(order)
            level.orders.append(order)
        order.size = size
        order.price = price

    def _side_levels(self, side: str) -> SortedDict:
        if side == "A":
            return self.offers
        if side == "B":
            return self.bids
        raise ValueError(f"Invalid {side =}")

    def _get_level(self, price: int, side: str) -> LevelOrders:
        levels = self._side_levels(side)
        if price not in levels:
            raise KeyError(f"No price level found for {price =} and {side =}")
        return levels[price]

    def _get_or_insert_level(self, price: int, side: str) -> LevelOrders:
        levels = self._side_levels(side)
        if price in levels:
            return levels[price]
        level = LevelOrders(price=price)
        levels[price] = level
        return level

    def _remove_level(self, price: int, side: str):
        levels = self._side_levels(side)
        levels.pop(price)


@dataclass
class Market:
    books: defaultdict[int, defaultdict[int, Book]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(Book)),
    )

    def get_books_by_pub(self, instrument_id: int) -> defaultdict[int, Book]:
        return self.books[instrument_id]

    def get_book(self, instrument_id: int, publisher_id: int) -> Book:
        return self.books[instrument_id][publisher_id]

    def bbo(
        self,
        instrument_id: int,
        publisher_id: int,
    ) -> tuple[PriceLevel | None, PriceLevel | None]:
        return self.books[instrument_id][publisher_id].bbo()

    def aggregated_bbo(
        self,
        instrument_id: int,
    ) -> tuple[PriceLevel | None, PriceLevel | None]:
        agg_bbo: list[PriceLevel | None] = [None, None]
        # max for bids, min for asks
        for idx, reducer in [(0, max), (1, min)]:
            all_best = [b.bbo()[idx] for b in self.books[instrument_id].values()]
            all_best = [b for b in all_best if b]
            if not all_best:
                continue
            best_price = reducer(b.price for b in all_best)
            best = [b for b in all_best if b.price == best_price]
            agg_bbo[idx] = PriceLevel(
                price=best_price,
                size=sum(b.size for b in best),
                count=sum(b.count for b in best),
            )
        return tuple(agg_bbo)

    def apply(self, mbo: db.MBOMsg):
        book = self.books[mbo.instrument_id][mbo.publisher_id]
        book.apply(
            ts_event=mbo.ts_event,
            action=mbo.action,
            side=mbo.side,
            order_id=mbo.order_id,
            price=mbo.price,
            size=mbo.size,
            flags=mbo.flags,
        )


class intraday_rec(IntEnum):
    timestamp = 0
    open = 1
    high = 2
    low = 3
    close = 4
    num_trades = 5
    total_vol = 6
    bid_vol = 7
    ask_vol = 8


class tas_rec(IntEnum):
    timestamp = 0
    price = 1
    qty = 2
    side = 3


bento_to_sierra_command_mapping = {
    "R": 1,  # clear book
    "AB": 2,  # add bid
    "AA": 3,  # add ask
    "MB": 4,  # modify bid
    "MA": 5,  # modify ask
    "CB": 6,  # cancel bid
    "CA": 7,  # cancel ask
}

sierra_to_bento_command_mapping = {
    v: k for k, v in bento_to_sierra_command_mapping.items()
}

sierra_global_epoch = datetime64("1899-12-30")

intraday_header_fmt = "4cIIHHI36c"
intraday_header_len = calcsize(intraday_header_fmt)

intraday_rec_fmt = "q4f4I"
intraday_rec_len = calcsize(intraday_rec_fmt)
intraday_rec_unpack = Struct(intraday_rec_fmt).unpack_from


def convert_sierra_timestamp_to_datetime(ts):
    return (
        (sierra_global_epoch + timedelta64(ts, "us"))
        .astype(datetime)
        .strftime("%Y-%m-%d %H:%M:%S.%f")
    )


def convert_to_sierra_timestamp(timestamp_str):
    sierra_epoch = sierra_global_epoch.tolist()
    sierra_epoch = datetime(
        sierra_epoch.year, sierra_epoch.month, sierra_epoch.day, tzinfo=timezone.utc
    )
    dt = datetime.fromisoformat(timestamp_str)
    # If dt is offset-naive, make it UTC aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    time_diff = dt - sierra_epoch  # Both are now UTC aware
    microseconds = time_diff.total_seconds() * 1e6
    return int(microseconds)


def get_header_bytes(fd):
    return fd.read(intraday_header_len)


def parse_tas_header(fd):
    header_bytes = fd.read(intraday_header_len)
    print(f"header -> {header_bytes}")
    header = Struct(intraday_header_fmt).unpack_from(header_bytes)
    return header


def parse_market_depth_file(filepath):
    rows = []
    with open(filepath, "rb") as input_file:
        header = input_file.read(64)
        print(header)
        header = struct.unpack("4I48s", header)
        while True:
            current = {}
            tick = input_file.read(24)
            if not tick:
                break
            src = struct.unpack("qbbhfII", tick)
            current["timestamp"] = src[0]
            current["command"] = src[1]
            current["flag"] = src[2]
            current["orders"] = src[3]
            current["price"] = src[4]
            current["quantity"] = src[5]
            rows.append(current)
    return rows


def get_market_depth_df_from_depth_file(filepath):
    print(f"make_market_depth_df_from_filepath -> {filepath}")
    rows = parse_market_depth_file(filepath)
    res = pd.DataFrame(rows)
    res["ts"] = res.timestamp.apply(convert_sierra_timestamp_to_datetime)
    return res


def bento_to_scid(bento_zst_path, target_path):
    print("load file")
    if os.path.exists(bento_zst_path):
        data = db.DBNStore.from_file(bento_zst_path)
    else:
        raise ValueError(f"data file {bento_zst_path} not found.")
    print("convert to df")
    bento = data.to_df()
    print("make scid")
    ticks_to_scid(primary_to_ticks(bento_to_primary(bento)), target_path)


def bento_to_depth(input_filepath, output_filepath, snapshot_size=100, n_states=-1):
    print("start bento to depth")
    if os.path.exists(input_filepath):
        data = db.DBNStore.from_file(input_filepath)
    else:
        raise ValueError(f"data file {input_filepath} not found.")
    os.system(f"bento-to-depth {input_filepath} temp.csv {snapshot_size} {n_states}")
    bento_depth = pd.read_csv("temp.csv")
    bento_depth["timestamp"] = bento_depth.timestamp.apply(
        lambda ts: convert_to_sierra_timestamp(str(pd.to_datetime(ts, unit="ns")))
    )
    bento_depth["timestamp"] = bento_depth.timestamp.apply(
        lambda ts: (ts // 1000) * 1000
    )
    bento_depth["timestamp"] = bento_depth.timestamp.astype(int)
    bento_depth["orders"] = bento_depth["orders"].astype(int)
    bento_depth["quantity"] = bento_depth["quantity"].astype(int)
    bento_depth = bento_depth.sort_values(["timestamp", "price"])
    depth_to_depth_file_for_sierra(bento_depth, output_filepath)


def bento_to_depth_slow(bento_zst_path, target_path, n_states=None):
    def make_decision_command(r):
        if pd.isna(r.side_p):
            return "AC"
        if pd.isna(r.side_c):
            return "CP"
        if r.side_p != r.side_c:
            return "CPMC"
        if r.quantity_p != r.quantity_c or r.orders_p != r.orders_c:
            return "MC"
        return "0"

    if os.path.exists(bento_zst_path):
        data = db.DBNStore.from_file(bento_zst_path)
    else:
        raise ValueError(f"data file {bento_zst_path} not found.")

    snapshot_size = 100  # number of levels bid/ask (200 total in this case)
    price_resolution = 1000000000  # as per bento docs

    init = True
    init_state = None
    counter = 0

    for first in data:
        break
    print(f"first -> {first}")
    instrument_id, publisher_id = first.instrument_id, first.publisher_id
    print(f"instrument_id -> {instrument_id}")
    print(f"publisher_id -> {publisher_id}")

    prev_timestamp = 0
    bento_depth = []
    prev = None

    market = Market()
    for mbo in ProgIter(data):
        market.apply(mbo)
        if mbo.flags & db.RecordFlags.F_LAST:
            diff = mbo.ts_event - prev_timestamp
            prev_timestamp = mbo.ts_event
            # check if within range of Sierra timestamps (if less than 1000 we need to aggregate the state)
            if diff < 1000:
                continue

            book = market.get_book(instrument_id, publisher_id).get_snapshot(
                snapshot_size
            )
            rows = [] if not init else [(0, 0, 0.0, "R")]
            for b in book:
                rows.append((b.bid_ct, b.bid_sz, b.bid_px / price_resolution, "B"))
                rows.append((b.ask_ct, b.ask_sz, b.ask_px / price_resolution, "A"))

            book_state = pd.DataFrame(rows)
            book_state.columns = ["orders", "quantity", "price", "side"]
            book_state = (
                book_state.sort_values("price", ascending=False)
                .reset_index()
                .drop(columns=["index"])
            )
            sierra_timestamp = (
                convert_to_sierra_timestamp(
                    str(pd.to_datetime(mbo.ts_event, unit="ns"))
                )
                // 1000
            ) * 1000
            book_state["timestamp"] = sierra_timestamp
            book_state = book_state[
                ["timestamp", "orders", "quantity", "price", "side"]
            ]

            if init:
                init_state = book_state
                init = False
                prev = init_state[init_state.side != "R"]
                init_depth = [
                    (
                        (r.timestamp, "R", 0, 0, 0.0, 0)
                        if r.side == "R"
                        else (
                            r.timestamp,
                            f"A{r.side}",
                            0,
                            r.orders,
                            r.price,
                            r.quantity,
                        )
                    )
                    for r in init_state.itertuples()
                ]
                bento_depth += init_depth
                continue

            current = book_state

            cols = ["orders", "quantity", "price", "side"]
            temp = pd.merge(
                prev[cols],
                current[cols],
                how="outer",
                on="price",
                suffixes=["_p", "_c"],
            )
            temp["decision"] = temp.apply(lambda r: make_decision_command(r), axis=1)

            current_depth = []
            current_timestamp = current.timestamp.unique()[0]
            for r in temp[temp.decision != "0"].itertuples():
                if r.decision == "CP":
                    current_depth.append(
                        (current_timestamp, f"C{r.side_p}", 1, 0, r.price, 0)
                    )
                elif r.decision == "AC":
                    current_depth.append(
                        (
                            current_timestamp,
                            f"A{r.side_c}",
                            1,
                            r.orders_c,
                            r.price,
                            r.quantity_c,
                        )
                    )
                elif r.decision == "CPMC":
                    current_depth.append(
                        (current_timestamp, f"C{r.side_p}", 1, 0, r.price, 0)
                    )
                    current_depth.append(
                        (
                            current_timestamp,
                            f"A{r.side_c}",
                            1,
                            r.orders_c,
                            r.price,
                            r.quantity_c,
                        )
                    )
                elif r.decision == "MC":
                    current_depth.append(
                        (
                            current_timestamp,
                            f"M{r.side_c}",
                            1,
                            r.orders_c,
                            r.price,
                            r.quantity_c,
                        )
                    )

            bento_depth += current_depth
            prev = current

            if n_states is None:
                continue

            counter += 1
            if counter >= n_states:
                print("n_states reached, break")
                break

    bento_depth = pd.DataFrame(bento_depth)
    bento_depth.columns = [
        "timestamp",
        "command",
        "flag",
        "orders",
        "price",
        "quantity",
    ]
    bento_depth["command"] = bento_depth.command.apply(
        lambda c: bento_to_sierra_command_mapping[c]
    )
    bento_depth["timestamp"] = bento_depth.timestamp.astype(int)
    bento_depth["orders"] = bento_depth.orders.astype(int)
    bento_depth["quantity"] = bento_depth.quantity.astype(int)
    bento_depth.to_csv("temp_slow.csv", index=False)
    print(f"shape bento_depth -> {bento_depth.shape}")
    first_ts, last_ts = convert_sierra_timestamp_to_datetime(
        bento_depth.timestamp.unique()[1]
    ), convert_sierra_timestamp_to_datetime(
        int(bento_depth.iloc[bento_depth.shape[0] - 1].timestamp)
    )
    print(f"first timestamp -> {first_ts}")
    print(f"last timestamp -> {last_ts}")
    depth_to_depth_file_for_sierra(bento_depth, target_path)


def bento_to_primary(bento):
    print("bento -> primary")
    bento["ts_event"] = bento.ts_event.astype(str)
    bento = bento.reset_index().drop(columns=["ts_recv"])
    cols_to_drop = [
        "ts_event",
        "rtype",
        "publisher_id",
        "instrument_id",
        "channel_id",
        "order_id",
        "ts_in_delta",
        "symbol",
    ]
    bento["timestamp"] = bento.ts_event.apply(convert_to_sierra_timestamp)
    bento["ts"] = bento.timestamp.apply(convert_sierra_timestamp_to_datetime)
    bento["ts"] = pd.to_datetime(bento.ts)
    bento = bento.drop(columns=cols_to_drop)
    bento = bento.rename(columns={"size": "size_"})
    bento = bento[bento.action != "T"]
    bento = bento[
        ["timestamp", "ts", "sequence", "flags", "price", "size_", "action", "side"]
    ]
    return bento


def primary_to_ticks(primary):
    print("primary -> ticks")
    ticks = primary[primary.action == "F"].copy()
    ticks["open"] = 0.0
    ticks["high"] = ticks.price
    ticks["low"] = ticks.price
    ticks["close"] = ticks.price
    ticks["num_trades"] = 1
    ticks["total_vol"] = ticks.size_
    ticks["bid_vol"] = ticks[["side", "size_"]].apply(
        lambda r: r.size if r.side == "B" else 0, axis=1
    )
    ticks["ask_vol"] = ticks[["side", "size_"]].apply(
        lambda r: r.size if r.side == "A" else 0, axis=1
    )
    ticks = ticks.drop(columns=["side", "price", "size_"])
    ticks = ticks.reset_index().drop(columns=["index"])
    return ticks


def ticks_to_scid(ticks, target_path):
    tas_recs = []
    for i in ProgIter(range(len(ticks))):
        tas_rec = (
            int(ticks.iloc[i].timestamp),
            ticks.iloc[i].open,
            ticks.iloc[i].high,
            ticks.iloc[i].low,
            ticks.iloc[i].close,
            int(ticks.iloc[i].num_trades),
            int(ticks.iloc[i].total_vol),
            int(ticks.iloc[i].bid_vol),
            int(ticks.iloc[i].ask_vol),
        )
        tas_recs.append(tas_rec)

    header = b"SCID8\x00\x00\x00(\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    print("write bytes to", target_path)
    tas_recs_bytes = header + b"".join(
        Struct(intraday_rec_fmt).pack(*rec) for rec in tas_recs
    )
    with open(target_path, "wb") as f:
        f.write(tas_recs_bytes)
    print("done.")


def depth_to_depth_file_for_sierra(depth, target_path):
    header = b"SCDD@\x00\x00\x00\x18\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    rec_format = "qbbhfII"
    recs = []
    for i in ProgIter(range(len(depth))):
        rec = (
            int(depth.iloc[i].timestamp),
            int(depth.iloc[i].command),
            int(depth.iloc[i].flag),
            int(depth.iloc[i].orders),
            float(depth.iloc[i].price),
            int(depth.iloc[i].quantity),
            0,
        )
        recs.append(rec)

    print("write bytes to", target_path)
    depth_bytes = header + b"".join(Struct(rec_format).pack(*rec) for rec in recs)
    with open(target_path, "wb") as f:
        f.write(depth_bytes)
    print("done.")


def bento_to_sierra(input_filepath, output_scid_file, output_depth_file):
    print("running -> bento to .scid (TODO: implement appending logic to the same scid file))")
    bento_to_scid(input_filepath, output_scid_file)
    print("running -> bento to .depth")
    bento_to_depth(input_filepath, output_depth_file)


if __name__ == "__main__":
    bento = pd.read_csv("../data/bento_full.csv")
    primary = bento_to_primary(bento)
    # ticks = primary_to_ticks(primary)
    # ticks_to_scid(ticks, "../data/bento-test.scid")
    depth = primary_to_depth(primary)
