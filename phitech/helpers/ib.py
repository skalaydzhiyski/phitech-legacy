from phitech.logger import logger
from phitech.const import *
from dotted_dict import DottedDict as dotdict
from ib_insync import IB, util
import pandas as pd

import os
import yaml
import re


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


def get_historical_bars(client, contract, end_date, duration, interval):
    res = client.reqHistoricalData(
        contract,
        endDateTime=make_date(end_date),
        durationStr=duration,
        barSizeSetting=interval,
        whatToShow="TRADES",
        useRTH=True,
    )
    res = util.df(res)
    res["date"] = pd.to_datetime(res["date"])
    res = res.set_index("date")
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
