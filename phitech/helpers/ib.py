from phitech.logger import logger
from phitech.const import *
from phitech.generators.helpers import parse_ticker_string
from dotted_dict import DottedDict as dotdict
from ib_insync import IB, util
from ib_insync.contract import *
import pandas as pd

import os
import yaml
import re
import datetime
import math
from progiter import ProgIter


def get_historical_bars_for_ticker_strings(client, ticker_strings):
    instruments = {}
    for ticker_str in ticker_strings:
        ticker, utype, _, exchange, interval, alias, start_date, end_date = parse_ticker_string(ticker_str)
        contract = Contract(secType=utype, symbol=ticker, exchange=exchange, currency="USD")
        client.qualifyContracts(contract)
        current = get_historical_bars(
            client, contract, start_date=start_date, end_date=end_date, interval=interval
        )
        instruments[alias] = current
    return instruments


def make_date(date_string):
    date_string = date_string.replace("-", "")
    if " " not in date_string:
        date_string += " 00:00:00"
    return date_string


def insync_interval_from_bar_type(bar_type):
    components = bar_type.split("-")
    size, agg = components[1], components[2]
    # only god knows why this is not consistent...
    if "second" in bar_type.lower():
        new_agg = INSYNC_MAPPING[agg]
    else:
        new_agg = INSYNC_MAPPING[agg] if size == "1" else f"{INSYNC_MAPPING[agg]}s"
    return f"{size} {new_agg}"


valid_intervals = {
    "5 secs",
    "10 secs",
    "15 secs",
    "30 secs",
    "1 min",
    "2 mins",
    "3 mins",
    "5 mins",
    "10 mins",
    "15 mins",
    "20 mins",
    "30 mins",
}


def get_historical_bars(client, contract, start_date, end_date, interval):
    logger.info(f"getting historical bars for -> {contract.symbol}")
    sd, ed = datetime.datetime.fromisoformat(start_date), datetime.datetime.fromisoformat(end_date)

    safe_intervals = ["hour", "day", "week", "month"]
    for si in safe_intervals:
        if si in interval:
            diff_days = int((ed - sd).days) + 1
            if diff_days >= 365:
                duration = f"{math.ceil(diff_days / 365)} Y"
            else:
                duration = f"{diff_days} D"

            res = get_historical_bars_default(client, contract, end_date, duration, interval)
            if " " in str(res.index.dtype):
                res.index = res.index.tz_convert(None)
            res = res[res.index >= sd]
            return res

    if interval not in valid_intervals:
        raise Exception("invalid interval")

    if "secs" in interval and (datetime.datetime.now() - sd).days > 6 * 30:
        raise Exception("data too old to be retrieved for `secs` interval")

    diff = int((ed - sd).days) + 1
    max_lookback_days = 3 if "secs" in interval else 20  # if "min"

    if diff > max_lookback_days:
        logger.info("multipart data pull")
        n_requests = diff // max_lookback_days + 1
        if n_requests > 100:
            raise Exception("too many requests required for date range")

        res = pd.DataFrame()
        for _ in ProgIter(range(n_requests)):
            current = get_historical_bars_default(
                client, contract, ed.strftime("%Y-%m-%d"), f"{max_lookback_days} D", interval
            )
            if current is None:
                raise Exception("IB returns None, probably data is too old for interval")
            ed = current.index.min()
            res = pd.concat([current, res])

        if " " in str(res.index.dtype):
            res.index = res.index.tz_convert(None)
        res = res[res.index >= sd]
        return res

    res = get_historical_bars_default(client, contract, end_date, f"{diff} D", interval)
    if " " in str(res.index.dtype):
        res.index = res.index.tz_convert(None)
    res = res[res.index >= sd]
    return res


def get_historical_bars_default(client, contract, end_date, duration, interval):
    res = client.reqHistoricalData(
        contract,
        endDateTime=make_date(end_date),
        durationStr=duration,
        barSizeSetting=interval,
        whatToShow="TRADES",
        useRTH=True,
        timeout=300,
    )
    res = util.df(res)
    res["date"] = pd.to_datetime(res["date"])
    res = res.set_index("date")
    res = res[[c for c in res.columns if c not in ["average", "barCount"]]]
    return res


def get_historical_ticks(client, contract, start_date, end_date, what_to_show="TRADES", number_of_ticks=1000):
    res = client.reqHistoricalTicks(
        contract=contract,
        startDateTime=make_date(start_date),
        endDateTime=make_date(end_date),
        whatToShow=what_to_show,  # BID_ASK, MIDPOINT, TRADES,
        numberOfTicks=number_of_ticks,
        useRth=True,
    )
    res = util.df(res)
    return res


def get_client(mode="paper_gateway", client_id=2):
    util.startLoop()
    client = IB()
    port = (4002 if "paper" in mode else 4001) if "gateway" in mode else (7497 if "live" in mode else 7496)
    client.connect(host="127.0.0.1", port=port, clientId=client_id, readonly=True)
    return client


def get_news(client, contract, start_date=None, end_date=None):
    start_date = make_date(start_date) if start_date else ""
    end_date = make_date(end_date) if end_date else ""

    providers = "+".join([provider.code for provider in client.reqNewsProviders()])
    logger.info(f"getting news from providers -> {providers}")

    news = client.reqHistoricalNews(
        contract.conId,
        providerCodes=providers,
        startDateTime=start_date,
        endDateTime=end_date,
        totalResults=100,
    )
    res = [(article.time, re.sub(r"{.*?}", "", article.headline)[1:]) for article in news]
    res = pd.DataFrame(res, columns=["time", "title"])
    return res
