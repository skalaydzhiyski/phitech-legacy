from phitech import conf, const
from phitech.helpers.glob import mkdir_or_replace, run_formatter
from phitech.generators.helpers import parse_sets_string
from phitech.generators.backtest import generate_backtest_runs
from phitech.generators.live import generate_live
from phitech.logger import logger
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

    logger.info("create backtest dir")
    backtest_files_to_create = [
        # "instruments.py",
        # "runner.py",
        "provider.py",
        "strategies.py",
    ]
    backtest_names = bot_def.backtest.runs
    for backtest_name in backtest_names:
        logger.info(f"create backtest -> `{backtest_name}`")
        current_backtest_root = f"{backtest_root}/{backtest_name}"
        mkdir_or_replace(current_backtest_root)
        logger.info("write root files")
        for fname in backtest_files_to_create:
            os.system(f"touch {current_backtest_root}/{fname}")

        logger.info("create sets dir")
        mkdir_or_replace(f"{current_backtest_root}/sets")
        backtest = conf.backtests[backtest_name]
        set_idxs = parse_sets_string(
            backtest.universe.instruments.sets, name=backtest.universe.instruments.name
        )
        for idx in set_idxs:
            logger.info(f"create dir for set -> {idx}")
            mkdir_or_replace(f"{current_backtest_root}/sets/set_{idx}")
            mkdir_or_replace(f"{current_backtest_root}/sets/set_{idx}/report")
            mkdir_or_replace(f"{current_backtest_root}/sets/set_{idx}/report/img")

    live_files_to_create = ["instruments.py", "provider.py", "runner.py", "strategies.py"]
    live_root = f"{bot_root}/live"
    mkdir_or_replace(live_root)
    logger.info("create live dir")
    for fname in live_files_to_create:
        os.system(f"touch {live_root}/{fname}")


def generate_bot(name):
    logger.info("generate backtests")
    generate_backtest_runs(name)

    logger.info("generate live")
    generate_live(name)

    logger.info("run formatter")
    run_formatter()
