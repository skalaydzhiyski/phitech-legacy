from phitech import conf, const
from phitech.logger import logger
from phitech.generators.helpers import write_to_file, filename_to_cls
from phitech.templates import (
    provider_template,
    backtest_instruments_template,
    backtest_instrument_stock_template,
    strategy_import_template,
    strategy_template,
    strategies_template,
    backtest_runner_template,
)


def generate_backtest_provider(backtest_def):
    provider_def = conf.providers[backtest_def.provider]
    return provider_template.format(
        host=provider_def.host,
        port=provider_def.port,
        client_id=backtest_def.broker.client_id,
    )


def get_instrument_strings_for_kind(kind, backtest_def):
    kind_instruments_def = conf.instruments[backtest_def.universe.instruments.name][kind]
    instrument_strings = []
    for ticker in kind_instruments_def.tickers:
        istr = ""
        if kind == "stocks":
            istr = backtest_instrument_stock_template.format(
                ticker=ticker,
                security_type=kind_instruments_def.contract.security_type,
                exchange=kind_instruments_def.contract.exchange,
                from_date=backtest_def.range.start_date,
                to_date=backtest_def.range.end_date,
            )
        elif kind == "future":
            raise NotImplementedError("not supported")
        instrument_strings.append(istr)
    return instrument_strings


def generate_backtest_instruments(backtest_def, bot_kind, bot_name, backtest_name):
    instrument_strings = []
    for kind in backtest_def.universe.instruments.kinds:
        instrument_strings += get_instrument_strings_for_kind(kind, backtest_def)

    instruments_str = "".join(instrument_strings)
    return backtest_instruments_template.format(
        bot_kind=bot_kind, bot_name=bot_name, backtest_name=backtest_name, instruments=instruments_str
    )


def generate_backtest_strategies(bot_def):
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


def generate_backtest(backtest_name, bot_name, bot_def):
    backtest_def = conf.backtests[backtest_name]
    base_backtest_path = f"bots/{bot_def.kind}/{bot_name}/backtest/{backtest_name}"

    logger.info("generate backtest provider")
    backtest_provider_str = generate_backtest_provider(backtest_def)
    write_to_file(backtest_provider_str, f"{base_backtest_path}/provider.py")

    logger.info("generate backtest instruments")
    backtest_instruments_str = generate_backtest_instruments(
        backtest_def, bot_def.kind, bot_name, backtest_name
    )
    write_to_file(backtest_instruments_str, f"{base_backtest_path}/instruments.py")

    logger.info("generate backtest strategies")
    backtest_strategies_str = generate_backtest_strategies(bot_def)
    write_to_file(backtest_strategies_str, f"{base_backtest_path}/strategies.py")

    logger.info("generate backtest runner")
    backtest_runner_str = backtest_runner_template.format(
        bot_kind=bot_def.kind,
        bot_name=bot_name,
        backtest_name=backtest_name,
        timeframe=backtest_def.sample.timeframe.capitalize(),
        compression=backtest_def.sample.compression,
    )
    write_to_file(backtest_runner_str, f"{base_backtest_path}/runner.py")


def generate_backtest_runs(name):
    bot_def = conf.bots[name]
    for backtest_run_name in bot_def.backtest.runs:
        logger.info(f"current -> `{backtest_run_name}`")
        generate_backtest(backtest_run_name, name, bot_def)
