from phitech.logger import logger
from phitech import const

import os
import json


def generate_exploration_notebook(name):
    fname = f"{const.BASE_NOTEBOOKS_PATH}/exploration/{name}.ipynb"
    os.sytem(f"cp {const.BASE_NOTEBOOKS_PATH}/base.ipynb {fname}")
    logger.info("done.")


def generate_strategy_notebook(name):
    strategy_path = f"{const.BASE_STRATEGIES_PATH}/{name}.py"
    logger.info(f"load strategy from -> `{strategy_path}`")
    with open(strategy_path, "r") as f:
        source_code = f.read().strip()

    base_nb_path = f"{const.BASE_NOTEBOOKS_PATH}/base.ipynb"
    logger.info("load base notebook json")
    with open(base_nb_path, "r") as f:
        base_notebook = json.load(f)

    strategy_path_cell = const.EMPTY_CODE_CELL.copy()
    strategy_path_cell["source"] = [f"""strategy_path = '{strategy_path}'"""]

    source_code_cell = const.EMPTY_CODE_CELL.copy()
    source_code_cell["source"] += [f"{line}\n" for line in source_code.split("\n")]

    runner_cell = const.EMPTY_CODE_CELL.copy()
    runner_cell["source"] = [
        f"write_prev_cell(strategy_path)\n",
        f"run_tmux_cmd('3:2.0', 'pt run bot --name bot1 --backtest bt1')",
    ]

    logger.info("add extra cells")
    base_notebook["cells"] += [strategy_path_cell, source_code_cell, runner_cell]

    strategy_notebook_path = f"{const.BASE_NOTEBOOKS_PATH}/strategies/{name}.ipynb"
    logger.info(f"write to -> {strategy_notebook_path}")
    with open(strategy_notebook_path, "w") as f:
        json.dump(base_notebook, f)
    logger.info("done.")
