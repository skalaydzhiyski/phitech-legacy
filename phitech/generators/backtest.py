from phitech import conf, const
from phitech.templates import (
    backtest_engine_template,
    backtest_bar_data_wrangler_template,
    backtest_provider_IB_template,
    backtest_runner_template,
    strategy_template,
    instruments_template,
)
from phitech.generators.helpers import (
    get_bar_types_for_symbol,
    write_to_file,
    generate_instruments,
    generate_strategies,
)
from phitech.logger import logger


def generate_backtest_engine(backtest_def):
    backtest_engine_str = backtest_engine_template.format(
        trader_id=backtest_def.trader_id,
        risk_engine_bypass=backtest_def.risk_engine.bypass,
        oms_type=backtest_def.venue.oms_type,
        account_type=backtest_def.venue.account_type,
        starting_balances=backtest_def.venue.starting_balances,
    )
    return backtest_engine_str


def generate_backtest_instruments(bot_def):
    return generate_instruments(bot_def, "SIM")


def generate_backtest_provider(backtest_name, backtest_def, bot_name, bot_kind):
    provider_def = conf.providers[backtest_def.provider]
    if provider_def.kind == "IB":
        if provider_def.wrangler.cls == "BarDataWrangler":
            wrangler = backtest_bar_data_wrangler_template.strip()
            backtest_provider_str = backtest_provider_IB_template.format(
                bot_kind=bot_kind,
                bot_name=bot_name,
                backtest_name=backtest_name,
                host=provider_def.host,
                port=provider_def.port,
                clientId=provider_def.clientId,
                readonly=provider_def.readonly,
                duration=backtest_def.duration,
                end_date=backtest_def.end_date,
                wrangler=wrangler,
            )
            return backtest_provider_str
        else:
            raise NotImplementedError("wrangler not implement yet")
    else:
        raise NotImplementedError("provider not implemented yet")


def generate_backtest_runner(backtest_name, bot_name, bot_kind):
    backtest_runner_str = backtest_runner_template.format(
        bot_kind=bot_kind,
        bot_name=bot_name,
        backtest_name=backtest_name,
        base_reports_path=f"./bots/{bot_kind}/{bot_name}/backtest/{backtest_name}/reports/",
    )
    return backtest_runner_str


def generate_backtest_strategies(strategy_defs, backtest_name, bot_name, bot_kind):
    strategy_imports, strategy_instances = generate_strategies(strategy_defs)
    instrument_bar_types_from = f"bots.{bot_kind}.{bot_name}.backtest.{backtest_name}.instruments"
    backtest_strategies_str = strategy_template.format(
        instrument_bar_types_from=instrument_bar_types_from,
        strategy_imports=strategy_imports,
        strategy_instances=strategy_instances,
    )
    return backtest_strategies_str


def generate_backtest(backtest_name, bot_name, bot_def):
    backtest_def = conf.backtests[backtest_name]
    base_backtest_path = f"bots/{bot_def.kind}/{bot_name}/backtest/{backtest_name}"

    logger.info("generate backtest engine")
    backtest_engine_str = generate_backtest_engine(backtest_def)
    write_to_file(backtest_engine_str, f"{base_backtest_path}/engine.py")

    logger.info("generate backtest instruments")
    backtest_instruments_str = generate_backtest_instruments(bot_def)
    write_to_file(backtest_instruments_str, f"{base_backtest_path}/instruments.py")

    logger.info("generate backtest provider")
    backtest_provider_str = generate_backtest_provider(backtest_name, backtest_def, bot_name, bot_def.kind)
    write_to_file(backtest_provider_str, f"{base_backtest_path}/provider.py")

    logger.info("generate backtest runner")
    backtest_runner_str = generate_backtest_runner(backtest_name, bot_name, bot_def.kind)
    write_to_file(backtest_runner_str, f"{base_backtest_path}/runner.py")

    logger.info("generate strategies")
    backtest_strategies_str = generate_backtest_strategies(
        bot_def.strategies, backtest_name, bot_name, bot_def.kind
    )
    write_to_file(backtest_strategies_str, f"{base_backtest_path}/strategies.py")


def generate_backtest_runs(name):
    bot_def = conf.bots[name]
    for run_backtest_name in bot_def.backtest.runs:
        logger.info(f"current -> `{run_backtest_name}`")
        generate_backtest(run_backtest_name, name, bot_def)
