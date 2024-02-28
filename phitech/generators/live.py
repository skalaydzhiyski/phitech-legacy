from phitech import conf, const
from phitech.templates import (
    live_node_template,
    live_runner_template,
    strategy_template,
)
from phitech.generators.helpers import (
    get_bar_types_for_symbol,
    write_to_file,
    generate_instruments,
    generate_strategies,
)
from phitech.logger import logger


def generate_live_instruments(bot_def):
    return generate_instruments(bot_def)


def generate_live_node(bot_def, bot_name):
    node_def = conf.nodes[bot_def.live.node]
    return live_node_template.format(
        bot_kind=bot_def.kind,
        bot_name=bot_name,
        host=node_def.host,
        port=node_def.port,
        client_id=bot_def.live.client_id,
        trader_id=bot_def.live.trader_id,
        trading_mode=node_def.trading_mode,
        read_only=node_def.read_only,
        ib_username_env=node_def.env.ib_username,
        ib_password_env=node_def.env.ib_password,
        ib_account_id_env=node_def.env.ib_account_id,
        handle_revised_bars=node_def.handle_revised_bars,
    )


def generate_live_strategies(strategy_defs, bot_def, bot_name):
    strategy_imports, strategy_instances = generate_strategies(strategy_defs)
    instrument_bar_types_from = f"bots.{bot_def.kind}.{bot_name}.live.instruments"
    backtest_strategies_str = strategy_template.format(
        instrument_bar_types_from=instrument_bar_types_from,
        strategy_imports=strategy_imports,
        strategy_instances=strategy_instances,
    )
    return backtest_strategies_str


def generate_live_runner(bot_def, bot_name):
    return live_runner_template.format(
        bot_kind=bot_def.kind,
        bot_name=bot_name,
    )


def generate_live(bot_name):
    bot_def = conf.bots[bot_name]
    base_live_path = f"bots/{bot_def.kind}/{bot_name}/live"

    logger.info("generate instruments")
    live_instruments_str = generate_live_instruments(bot_def)
    write_to_file(live_instruments_str, f"{base_live_path}/instruments.py")

    logger.info("generate live node")
    live_node_str = generate_live_node(bot_def, bot_name)
    write_to_file(live_node_str, f"{base_live_path}/node.py")

    logger.info("generate live strategies")
    live_strategies_str = generate_live_strategies(bot_def.strategies, bot_def, bot_name)
    write_to_file(live_strategies_str, f"{base_live_path}/strategies.py")

    logger.info("generate live runner")
    live_runner_str = generate_live_runner(bot_def, bot_name)
    write_to_file(live_runner_str, f"{base_live_path}/runner.py")
