from phitech.logger import logger
from phitech import conf
from dotted_dict import DottedDict as dotdict

import os
import yaml


def get_ticker_strings_for_instruments(instruments_name, set_idx=None):
    sets = conf.instruments[instruments_name].sets
    if set_idx is None:
        return [s.tickers for s in sets]
    return sets[set_idx].tickers
