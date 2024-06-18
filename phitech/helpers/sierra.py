from phitech.logger import logger_lib as logger
import numpy as np
from numpy import datetime64, timedelta64
import pandas as pd
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from numpy import datetime64, timedelta64
from os import fstat
from struct import calcsize, Struct
from progiter import ProgIter


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


sierra_global_epoch = datetime64("1899-12-20")

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


def primary_to_scid(primary, target_scid_path):
    primary = primary_to_ticks(primary)
    tas_recs = []
    for i in ProgIter(range(len(primary))):
        tas_rec = (
            int(primary.iloc[i].timestamp),
            primary.iloc[i].open,
            primary.iloc[i].high,
            primary.iloc[i].low,
            primary.iloc[i].close,
            int(primary.iloc[i].num_trades),
            int(primary.iloc[i].total_vol),
            int(primary.iloc[i].bid_vol),
            int(primary.iloc[i].ask_vol),
        )
        tas_recs.append(tas_rec)

    header = b"SCID8\x00\x00\x00(\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

    print("Writing bytes to", target_scid_path)
    tas_recs_bytes = header + b"".join(
        Struct(intraday_rec_fmt).pack(*rec) for rec in tas_recs
    )
    with open(target_scid_path, "wb") as f:
        f.write(tas_recs_bytes)
    print("done.")


def parse_ticks_from_scid(fd):
    fstat(fd.fileno())
    tas_recs = []
    while intraday_rec_bytes := fd.read(intraday_rec_len):
        ir = intraday_rec_unpack(intraday_rec_bytes)
        tas_rec = (
            ir[intraday_rec.timestamp],
            ir[intraday_rec.open],
            ir[intraday_rec.high],
            ir[intraday_rec.low],
            ir[intraday_rec.close],
            ir[intraday_rec.num_trades],
            ir[intraday_rec.total_vol],
            ir[intraday_rec.bid_vol],
            ir[intraday_rec.ask_vol],
        )
        tas_recs.append(tas_rec)
    return tas_recs


def scid_to_ticks(filepath):
    with open(filepath, "rb") as f:
        parse_tas_header(f)
        res = parse_ticks_from_scid(f)
        res = pd.DataFrame(
            res,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "num_trades",
                "total_vol",
                "bid_vol",
                "ask_vol",
            ],
        )

    res["ts"] = res.timestamp.apply(convert_sierra_timestamp_to_datetime)
    return res


def sierra_to_ticks(path, target_date_string):
    res = scid_to_ticks(path)
    res = res[res.ts.str.contains(target_date_string)]
    res = res.reset_index().drop(columns=["index"])
    return res


def bento_to_ticks(bento_path):
    print(f"loading data from -> {bento_path}")
    bento_full = pd.read_csv(bento_path)
    bento_full = bento_full[
        [
            col
            for col in bento_full.columns
            if col
            not in ("rtype", "publisher_id", "instrument_id", "channel_id", "order_id")
        ]
    ]
    bento_full = bento_full.rename(columns={"ts_event": "timestamp"})
    print(f"bento data loaded -> {bento_full.shape}")

    print("filter out market depth and unnecessary columns")
    bento_ticks = bento_full[bento_full.action == "F"]
    bento_ticks = bento_ticks[
        [
            c
            for c in bento_ticks.columns
            if c not in ("action", "flags", "ts_in_delta", "sequence")
        ]
    ]
    bento_ticks["timestamp"] = bento_ticks.timestamp.apply(
        lambda t: convert_to_sierra_timestamp(t)
    )
    # NOTE: here we set the open -> 0, high = low = close (this might be an assumption worth revisiting)
    bento_ticks["open"] = 0.0
    bento_ticks["high"] = bento_ticks.price
    bento_ticks["low"] = bento_ticks.price
    bento_ticks["close"] = bento_ticks.price
    bento_ticks["num_trades"] = 1
    bento_ticks["total_vol"] = bento_ticks["size"]
    bento_ticks["bid_vol"] = bento_ticks[["side", "size"]].apply(
        lambda r: r.size if r.side == "B" else 0, axis=1
    )
    bento_ticks["ask_vol"] = bento_ticks[["side", "size"]].apply(
        lambda r: r.size if r.side == "A" else 0, axis=1
    )
    bento_ticks = bento_ticks.drop(columns=["side", "price", "size", "symbol"])
    bento_ticks = bento_ticks.reset_index().drop(columns=["index"])
    bento_ticks["ts"] = bento_ticks.timestamp.apply(
        convert_sierra_timestamp_to_datetime
    )
    return bento_ticks


def ticks_to_primary(ticks):
    ticks["price"] = ticks["close"]
    ticks["side"] = ticks[["bid_vol", "ask_vol"]].apply(
        lambda r: "B" if r.bid_vol != 0 else "A", axis=1
    )
    ticks["action"] = "F"
    ticks["size"] = ticks["total_vol"]
    ticks["ts"] = ticks.timestamp.apply(convert_sierra_timestamp_to_datetime)
    ticks = ticks[
        [
            col
            for col in ticks.columns
            if col
            not in (
                "open",
                "high",
                "low",
                "close",
                "num_trades",
                "bid_vol",
                "ask_vol",
                "total_vol",
            )
        ]
    ]
    return ticks


def primary_to_ticks(primary):
    ticks = primary.copy()
    ticks["open"] = 0.0
    ticks["high"] = ticks.price
    ticks["low"] = ticks.price
    ticks["close"] = ticks.price
    ticks["num_trades"] = 1
    ticks["total_vol"] = ticks["size"]
    ticks["bid_vol"] = ticks[["side", "size"]].apply(
        lambda r: r.size if r.side == "B" else 0, axis=1
    )
    ticks["ask_vol"] = ticks[["side", "size"]].apply(
        lambda r: r.size if r.side == "A" else 0, axis=1
    )
    ticks = ticks.drop(columns=["side", "price", "size"])
    ticks = ticks.reset_index().drop(columns=["index"])
    return ticks


def sierra_to_primary(path, target_date_string):
    ticks = sierra_to_ticks(path, target_date_string)
    return ticks_to_primary(ticks)


def bento_to_primary(bento_path):
    print("make ticks")
    ticks = bento_to_ticks(bento_path)
    print("make primary")
    return ticks_to_primary(ticks)
