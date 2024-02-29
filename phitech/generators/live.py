from phitech import conf, const
from phitech.generators.helpers import (
    write_to_file,
    filename_to_cls
)
from phitech.templates import (
    provider_template,
    live_instruments_template,
    live_instrument_stock_template,
    strategy_import_template,
    strategy_template,
    strategies_template,
    live_runner_template,

)
from phitech.logger import logger


def generate_live_provider(bot_def):
    provider_def = conf.providers[bot_def.live.provider]
    return provider_template.format(
        host=provider_def.host,
        port=provider_def.port,
        client_id=bot_def.live.client_id,
    )

def get_instrument_strings_for_kind(bot_def, kind):
    kind_instruments_def = conf.instruments[bot_def.live.universe.instruments.name][kind]
    instrument_strings = []
    for ticker in kind_instruments_def.tickers:
        istr = ""
        if kind == "stocks":
            istr = live_instrument_stock_template.format(
                ticker=ticker,
                security_type=kind_instruments_def.contract.security_type,
                exchange=kind_instruments_def.contract.exchange,
                tradename=bot_def.live.tradename,
            )
        elif kind == "future":
            raise NotImplementedError("not supported")
        instrument_strings.append(istr)
    return instrument_strings


def generate_live_instruments(bot_def, bot_name):
    instrument_strings = []
    for kind in bot_def.live.universe.instruments.kinds:
        instrument_strings += get_instrument_strings_for_kind(bot_def, kind)

    instruments_str = "".join(instrument_strings)
    return live_instruments_template.format(
        bot_kind=bot_def.kind, bot_name=bot_name, instruments=instruments_str
    )

def generate_live_strategies(bot_def):
    strategy_imports = "\n".join(
        [
            strategy_import_template.format(
                strategy_kind=sdef.kind,
                strategy_name=sdef.name,
                strategy_cls=filename_to_cls(sdef.name),
            ).strip()
            for sdef in bot_def.strategies
        ]
    )
    strategies = "".join(
        [
            strategy_template.format(
                strategy_cls=filename_to_cls(sdef.name),
                strategy_config=conf.strategy_configs[sdef.config].config.to_dict(),
            )
            for sdef in bot_def.strategies
        ]
    )
    return strategies_template.format(
        strategy_imports=strategy_imports,
        strategies=strategies,
    )

def generate_live(bot_name):
    bot_def = conf.bots[bot_name]
    base_live_path = f"bots/{bot_def.kind}/{bot_name}/live"

    logger.info("generate live node")
    live_node_str = generate_live_provider(bot_def)
    write_to_file(live_node_str, f"{base_live_path}/provider.py")

    logger.info("generate instruments")
    live_instruments_str = generate_live_instruments(bot_def, bot_name)
    write_to_file(live_instruments_str, f"{base_live_path}/instruments.py")

    logger.info("generate live strategies")
    live_strategies_str = generate_live_strategies(bot_def)
    write_to_file(live_strategies_str, f"{base_live_path}/strategies.py")

    logger.info("generate live runner")
    live_runner_str = live_runner_template.format(
        bot_kind=bot_def.kind,
        bot_name=bot_name,
        timeframe=bot_def.live.sample.timeframe.capitalize(),
        compression=bot_def.live.sample.compression,
    )
    write_to_file(live_runner_str, f"{base_live_path}/runner.py")
