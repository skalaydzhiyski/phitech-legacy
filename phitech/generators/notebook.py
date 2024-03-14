from phitech.logger import logger_lib as logger
from phitech import const
from phitech import conf
from phitech import templates

import os
import json


def make_cell(text, kind="code"):
    return {
        "cell_type": kind,
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text_to_cell_list(text),
    }


def generate_exploration_notebook(name):
    path = f"{const.BASE_NOTEBOOKS_PATH}/exploration/{name}.ipynb"
    notebook = const.NOTEBOOK_BASE.copy()
    cells = [
        make_cell(templates.notebook_base_imports),
        make_cell(templates.notebook_client_instance),
        make_cell(templates.notebook_ticker_strings),
        make_cell(templates.notebook_instruments),
        make_cell("### Strategy", kind="markdown"),
        make_cell(templates.blank_strategy_template.format(strategy_name="SimpleStrategy")),
        make_cell("### Run", kind="markdown"),
        make_cell(templates.notebook_single_backtest_runner),
        make_cell(templates.notebook_single_backtest_perf),
        make_cell("### Analysis", kind="markdown"),
    ]
    notebook["cells"] = cells
    logger.info(f"write to path -> {path}")
    with open(path, "w") as f:
        json.dump(notebook, f)


def text_to_cell_list(input_text):
    lines = input_text.strip().split("\n")
    return [f"{line}\n" if idx != len(lines) - 1 else line for idx, line in enumerate(lines)]
