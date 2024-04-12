from phitech import conf, const
from phitech.logger import logger_lib as logger
from phitech.generators.helpers import (
    write_to_file,
    filename_to_cls,
    parse_ticker_string,
    parse_tradingview_ticker_string,
)
from phitech.templates import (
    backtest_provider_template,
    backtest_runner_template_new,
    backtest_tradingview_data_template,
)


def generate_backtest_provider(backtest_def):
    provider_def = conf.providers[backtest_def.provider]
    return backtest_provider_template.format(
        provider_name=backtest_def.provider,
        client_id=backtest_def.broker.client_id,
    )


def generate_backtest(backtest_name, bot_name, bot_def):
    backtest_def = conf.backtests[backtest_name]

    root_backtest_path = f"bots/{bot_def.kind}/{bot_name}/backtest"
    base_backtest_path = f"{root_backtest_path}/{backtest_name}"

    logger.info("generate backtest provider")
    backtest_provider_str = generate_backtest_provider(backtest_def)
    write_to_file(backtest_provider_str, f"{root_backtest_path}/provider.py")

    logger.info("generate backtest runner")
    backtest_runner_str = backtest_runner_template_new.format(
        strategy_kind=bot_def.strategy.kind,
        strategy_name=bot_def.strategy.name,
        strategy_cls=filename_to_cls(bot_def.strategy.name),
        bot_kind=bot_def.kind,
        bot_name=bot_name,
        backtest_name=backtest_name,
        instruments_name=backtest_def.universe.instruments.name,
        strategy_conf=conf.strategy_configs[bot_def.strategy.config].config.to_dict(),
    )
    write_to_file(backtest_runner_str, f"{base_backtest_path}/runner.py")


def generate_backtests(name):
    bot_def = conf.bots[name]
    for backtest_name in bot_def.backtest:
        logger.info(f"current -> `{backtest_name}`")
        generate_backtest(backtest_name, name, bot_def)
