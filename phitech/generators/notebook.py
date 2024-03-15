from phitech.logger import logger_lib as logger
from phitech import const
from phitech import conf
from phitech import templates
from phitech.generators.helpers import filename_to_cls

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


def generate_strategy_notebook(name, instr_name, strategy_kind):
    notebook_kind_path = f"{const.BASE_NOTEBOOKS_PATH}/strategies/{strategy_kind}"
    if not os.path.exists(notebook_kind_path):
        logger.info(f'kind path not found, creating -> {notebook_kind_path}')
        os.mkdir(notebook_kind_path)

    strategy_path =  f"{const.BASE_STRATEGIES_PATH}/{strategy_kind}/{name}.py"
    with open(strategy_path, 'r') as f:
        strategy_str = f.read()

    strategy_str = f'#%%writefile {strategy_path}\n{strategy_str}'

    notebook_path = f"{const.BASE_NOTEBOOKS_PATH}/strategies/{strategy_kind}/{name}.ipynb"
    notebook = const.NOTEBOOK_BASE.copy()
    cells = [
        make_cell(templates.notebook_base_imports),
        make_cell(templates.notebook_client_instance),
        make_cell(templates.notebook_ticker_strings.format(instruments_name=instr_name)),
        make_cell(templates.notebook_instruments),
        make_cell("### Strategy", kind="markdown"),
        make_cell(strategy_str),
        make_cell("### Run", kind="markdown"),
        make_cell(templates.notebook_single_backtest_runner.format(
            strategy_cls=filename_to_cls(name),
            strategy_config="{}"
        )),
        make_cell(templates.notebook_single_backtest_perf),
        make_cell("### Explore", kind="markdown"),
    ]
    notebook["cells"] = cells
    logger.info(f"write to path -> {notebook_path}")
    with open(notebook_path, "w") as f:
        json.dump(notebook, f)


def generate_exploration_notebook(name, instr_name):
    path = f"{const.BASE_NOTEBOOKS_PATH}/exploration/{name}.ipynb"
    notebook = const.NOTEBOOK_BASE.copy()
    cells = [
        make_cell(templates.notebook_base_imports),
        make_cell(templates.notebook_client_instance),
        make_cell(templates.notebook_ticker_strings.format(instruments_name=instr_name)),
        make_cell(templates.notebook_instruments),
        make_cell("### Strategy", kind="markdown"),
        make_cell(templates.blank_strategy_template.format(strategy_name="SimpleStrategy")),
        make_cell("### Run", kind="markdown"),
        make_cell(templates.notebook_single_backtest_runner.format(
            strategy_cls=filename_to_cls(name),
            strategy_config="{}"
        )),
        make_cell(templates.notebook_single_backtest_perf),
        make_cell("### Explore", kind="markdown"),
    ]
    notebook["cells"] = cells
    logger.info(f"write to path -> {path}")
    with open(path, "w") as f:
        json.dump(notebook, f)


def text_to_cell_list(input_text):
    lines = input_text.strip().split("\n")
    return [f"{line}\n" if idx != len(lines) - 1 else line for idx, line in enumerate(lines)]
