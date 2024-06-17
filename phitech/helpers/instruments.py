from phitech.logger import logger_lib as logger
from phitech import conf, const
from dotted_dict import DottedDict as dotdict

import os
import yaml


def get_ticker_strings_for_instruments(instruments_name, set_idx=None):
    sets = conf.instruments[instruments_name].sets
    if set_idx is None:
        return [s.tickers for s in sets]
    return sets[set_idx].tickers


def make_ticker_strings(
    tickers, underlying_type, live_type, timeframes, aliases, ranges
):
    logger.info("generate sets")
    ticker_strings = []
    for ts in tickers:
        current = [
            f"{t}.{underlying_type}.{live_type}.{tf}" for t, tf in zip(ts, timeframes)
        ]
        for l, r in ranges:
            current_string = [f"{x}|{l}/{r}|{a}" for x, a in zip(current, aliases)]
            ticker_strings.append(current_string)
    return ticker_strings


def make_instruments_definition(name, ticker_strings):
    sets = [{"tickers": tickers} for tickers in ticker_strings]
    sets = {"sets": sets}
    path = f"{const.BASE_DEFINITIONS_PATH}/instruments/{name}.yml"
    logger.info(f"write to -> {path}")
    with open(path, "w") as f:
        yaml.dump(sets, f)
