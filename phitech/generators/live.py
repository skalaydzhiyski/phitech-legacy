from phitech import conf, const
from phitech.generators.helpers import (
    write_to_file,
)
from phitech.logger import logger


def generate_live(bot_name):
    return
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
