from phitech import conf
from phitech.logger import logger
from phitech.templates import (
    instruments_template,
    strategy_import_template,
    strategy_instance_template,
)


def write_to_file(string_content, filepath):
    with open(filepath, "w") as f:
        f.write(string_content)


def get_bar_types_for_symbol(instrument_id, symbol, venue, bar_types, strategy_defs):
    all_bar_types = []
    for sdef in strategy_defs:
        symbol_bar_type = bar_types[sdef.bar_types].to_dict()[instrument_id]
        current = f"{symbol}.{venue}-{symbol_bar_type}"
        all_bar_types.append(current)
    return list(set(all_bar_types))


def generate_strategies(strategy_defs):
    strategy_instances = []
    for sdef in strategy_defs:
        config = conf.strategy_configs[sdef.config].config
        kwargs = ",".join([f'{k}="{v}"' if type(v) == str else f"{k}={v}" for k, v in config.items()])
        strategy_instance = strategy_instance_template.format(
            strategy_name=sdef.name,
            kwargs=kwargs,
        )
        strategy_instances.append(strategy_instance)

    strategy_imports = "\n".join(
        [strategy_import_template.format(strategy_name=sdef.name) for sdef in strategy_defs]
    )
    strategy_instances = "\n".join(strategy_instances)
    return strategy_imports, strategy_instances


def generate_instruments(bot_def, venue=None):
    instruments_tuple_list = []
    instruments = conf.instruments[bot_def.universe.instruments]
    for instrument_id, contract_def in instruments.items():
        logger.info(f"current -> `{contract_def.contract.symbol}`")
        venue_ = venue or contract_def.contract.primaryExchange
        bar_types = get_bar_types_for_symbol(
            instrument_id, contract_def.contract.symbol, venue_, conf.bar_types, bot_def.strategies
        )
        instrument_tuple = tuple(contract_def.contract.to_dict().values()) + (venue_,) + (bar_types,)
        instruments_tuple_list.append(instrument_tuple)
        logger.info(instrument_tuple)

    backtest_instruments_str = instruments_template.format(instruments_tuple_list=instruments_tuple_list)
    return backtest_instruments_str
