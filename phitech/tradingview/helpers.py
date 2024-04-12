from phitech.tradingview.scanner import get_all_symbols
from phitech.logger import logger_lib as logger
from phitech.tradingview.query import Query, Column
from phitech.tradingview.scanner import COLUMNS
from phitech import const

from tenacity import retry, wait_fixed
from progiter import ProgIter
import pandas as pd
import numpy as np


@retry(wait=wait_fixed(4))
def _check_ib_tradable(ticker, exchange, client):
    res = client.reqMatchingSymbols(ticker)
    res = [r for r in res if r.contract.symbol == ticker and r.contract.secType == "STK"]
    if len(res) > 1:
        exchanges = [exchange, "ARCA"] if exchange == "NYSE" else [exchange]
        res = [r for r in res if r.contract.primaryExchange in exchanges]
    if len(res) > 1:
        logger.error("len bigger than 1, not a perfect match -> investigate")
        assert False
    elif res == []:
        return False, False
    return True, "CFD" in res[0].derivativeSecTypes


def _find_tradable_contracts(universe, client):
    ib_tradable, ib_tradable_cfd = [], []
    for ticker, exchange in ProgIter(universe[["ticker", "exchange"]].values):
        it, icfd = _check_ib_tradable(ticker, exchange, client)
        ib_tradable.append(it)
        ib_tradable_cfd.append(icfd)

    universe["is_ib"] = ib_tradable
    universe["is_ib_cfd"] = ib_tradable_cfd
    universe = universe[universe.is_ib_tradable == True]
    universe = universe.reset_index().drop(columns=["index"])
    return universe


def _query_universe():
    logger.info("get all tickers from -> `NYSE, AMEX, NASDAQ`")
    query = Query().select(*const.UNIVERSE_COLUMNS)
    universe = query.get_scanner_data()[1]
    universe = universe.rename(columns={"name": "ticker", "market_cap_basic": "market_cap"})
    universe["market_cap"] = universe.market_cap.apply(lambda x: 0 if np.isnan(x) else int(x))
    return universe


def get_scanner_data(query):
    res = query.get_scanner_data()[1]
    res = res.rename(columns={"name": "ticker"})
    return res


def get_tradable_universe(rebuild=False, client=None):
    universe = _query_universe()
    if rebuild:
        logger.info("check tradable in IB")
        universe = _find_tradable_contracts(universe, client)
        logger.info("check ETF")
        universe["is_etf"] = False
        universe.loc[universe.description.str.contains("ETF"), "is_etf"] = True
        universe.to_csv(const.UNIVERSE_PATH, index=False)
    else:
        universe = pd.read_csv(const.UNIVERSE_PATH)
    return universe


def get_universe():
    return _query_universe()


def get_available_columns():
    return list(COLUMNS.values())


def get_more_information(input_df, columns=None):
    if not columns:
        return input_df

    if "name" not in columns:
        columns.append("name")

    query = Query().select(*columns)
    query_df = query.get_scanner_data()[1]
    res = pd.merge(input_df, query_df, left_on="ticker", right_on="name")
    res = res[[c for c in res.columns if c != "name"]]
    return res
