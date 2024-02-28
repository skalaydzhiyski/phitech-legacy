from phitech.helpers.glob import parse_yaml, make_dot_children, validate_def_filename
from dotted_dict import DottedDict as dotdict
from phitech import const

import os


bots = parse_yaml(f"{const.BASE_DEFINITIONS_PATH}/bots.yml", dot=False)
bots = make_dot_children(bots)

strategy_configs = parse_yaml(f"{const.BASE_DEFINITIONS_PATH}/strategy_configs.yml")
strategy_configs = make_dot_children(strategy_configs)

providers = parse_yaml(f"{const.BASE_DEFINITIONS_PATH}/providers.yml")
providers = make_dot_children(providers)

backtests = parse_yaml(f"{const.BASE_DEFINITIONS_PATH}/backtests.yml")
backtests = make_dot_children(backtests)

# This can be done better
instruments = {}
for current in os.listdir(f"{const.BASE_DEFINITIONS_PATH}/instruments"):
    if not validate_def_filename(current):
        continue
    name = current.split(".")[0]
    instruments[name] = parse_yaml(f"{const.BASE_DEFINITIONS_PATH}/instruments/{current}")
