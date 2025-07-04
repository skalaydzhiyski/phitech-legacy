from phitech import conf, const
from phitech.helpers.glob import mkdir_or_replace, run_formatter
from phitech.generators.backtest import generate_backtests
from phitech.generators.live import generate_live
from phitech.logger import logger_lib as logger
from dotted_dict import DottedDict as dotdict

import os


def generate_bot_directory_structure(name):
    bot_def = conf.bots[name]
    kind_path = f"{const.BASE_BOTS_PATH}/{bot_def.kind}"
    if not os.path.exists(kind_path):
        os.mkdir(kind_path)

    bot_root = f"{kind_path}/{name}"
    mkdir_or_replace(bot_root)

    backtest_root = f"{bot_root}/backtest"
    mkdir_or_replace(backtest_root)
    mkdir_or_replace(f"{backtest_root}/report")

    notebooks_root = f"{bot_root}/notebooks"
    mkdir_or_replace(notebooks_root)

    logger.info("create backtest dir")
    backtest_files_to_create = [
        "runner.py",
    ]
    backtest_names = bot_def.backtest
    for backtest_name in backtest_names:
        logger.info(f"create backtest -> `{backtest_name}`")
        current_backtest_root = f"{backtest_root}/{backtest_name}"
        mkdir_or_replace(current_backtest_root)
        logger.info("write root files")
        for fname in backtest_files_to_create:
            os.system(f"touch {current_backtest_root}/{fname}")

    logger.info("create provider")
    os.system(f"touch {backtest_root}/provider.py")

    live_files_to_create = ["instruments.py", "provider.py", "runner.py"]
    live_root = f"{bot_root}/live"
    mkdir_or_replace(live_root)
    logger.info("create live dir")
    for fname in live_files_to_create:
        os.system(f"touch {live_root}/{fname}")


def generate_bot(name):
    logger.info("generate backtests")
    generate_backtests(name)

    logger.info("generate live")
    generate_live(name)

    logger.info("run formatter")
    run_formatter()
