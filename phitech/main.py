from phitech.logger import logger
from phitech.banner import BANNER
from phitech.generators.helpers import filename_to_cls
import click

import os
import sys
import yaml
import subprocess as sp
import time


@click.group("cli")
def cli():
    pass


@cli.command("info")
def info():
    # think about how we can use rich to print the banner in bold white.
    for line in BANNER.split("\n"):
        logger.info(f"\033[1m{line}\033[0m")
    logger.info("\t   Phi Technologies.\n")


@cli.group("make", help="Generator")
def make():
    pass


@cli.group("run", help="Runner")
def run():
    pass


@run.command(help="Run a bot backtest or live.")
def ide():
    logger.info("check jupyter and python same path")
    python_path = sp.run(["which", "python"], capture_output=True, text=True).stdout.strip()
    jupyter_path = sp.run(["which", "python"], capture_output=True, text=True).stdout.strip()
    assert python_path.split("/")[:-1] == jupyter_path.split("/")[:-1]
    logger.info("running jupyter lab")
    os.system("jupyter lab .")


@run.command(help="Run a bot backtest or live.")
@click.option("--name", required=True, help="The name of the bot")
@click.option("--backtest", required=False, help="The comma separated list of backtests to run.")
@click.option("--live", is_flag=True, required=False, help="Run the bot live")
def bot(name, backtest=None, live=False):
    from phitech import conf

    logger.info('boot engine')
    os.system('pt info')

    bot_def = conf.bots[name]
    if live:
        logger.info(f"start live execution of -> `{name}`")
        live_run_cmd = f"python3 bots/{bot_def.kind}/{name}/live/runner.py"
        os.system(live_run_cmd)
    else:
        logger.info(f"run backtests for -> `{name}`")
        backtests = backtest.split(",")
        for bt_name in backtests:
            logger.info(f"run backtest -> `{bt_name}`")
            base_sets_path = f"bots/{bot_def.kind}/{name}/backtest/{bt_name}/sets"
            logger.info(f"run sets for -> {bt_name}")
            for set_dir in sorted(os.listdir(base_sets_path)):
                logger.info(f"run set -> {set_dir.split('_')[-1]}")
                bt_run_cmd = f"python {base_sets_path}/{set_dir}/runner.py"
                os.system(bt_run_cmd)
                time.sleep(1)
        logger.info("done.")


@make.command(help="Generate a template from `phitech-templates`")
@click.option("--name", required=True, help="The name of the template")
def template(name):
    logger.info(f"generate template `{name}`")
    templates_repository = "git@github.com:skalaydzhiyski/phitech-templates.git"
    script = f"""
    git clone {templates_repository};
    cp -r phitech-templates/{name} ./;
    rm -rf phitech-templates;
    """
    os.system(script)
    logger.info("Do not forget to `export PYTHONPATH=$PWD` from within your new project")
    logger.info("done.")


@make.command(help="Generate a strategy skeleton")
@click.option("--name", required=True, help="The name of the strategy")
@click.option("--kind", required=True, help="The kind of the strategy")
def strategy(name, kind):
    from phitech import const
    from phitech.templates import blank_strategy_template

    kind_path = f"{const.BASE_STRATEGIES_PATH}/{kind}"
    if not os.path.exists(kind_path):
        logger.info("kind path does not exists, generate.")
        os.system(f"mkdir {kind_path}")

    strategy_path = f"{kind_path}/{name}.py"
    logger.info(f"generate strategy -> `{strategy_path}`")
    with open(strategy_path, "w") as f:
        strategy_str = blank_strategy_template.format(strategy_name=filename_to_cls(name))
        f.write(strategy_str)

    logger.info("done.")


@make.command(help="Generate a indicator skeleton")
@click.option("--name", required=True, help="The name of the indicator")
@click.option("--kind", required=True, help="The kind of the indicator")
@click.option("--line-name", required=True, help="The line name of the indicator (for use in a strategy)")
def indicator(name, kind, line_name):
    from phitech import const
    from phitech.templates import blank_indicator_template

    kind_path = f"{const.BASE_INDICATORS_PATH}/{kind}"
    if not os.path.exists(kind_path):
        logger.info("kind path does not exists, generate.")
        os.system(f"mkdir {kind_path}")

    indicator_path = f"{kind_path}/{name}.py"
    logger.info(f"generate indicator -> `{indicator_path}`")
    with open(indicator_path, "w") as f:
        indicator_str = blank_indicator_template.format(
            indicator_name=filename_to_cls(name, suffix="Indicator"), indicator_line_name=line_name
        )
        f.write(indicator_str)


@make.command(help="Generate a analyzer skeleton")
@click.option("--name", required=True, help="The name of the analyzer")
def analyzer(name):
    from phitech import const
    from phitech.templates import blank_analyzer_template

    analyzer_path = f"{const.BASE_ANALYZERS_PATH}/{name}.py"
    logger.info(f"generate analyzer -> `{analyzer_path}`")
    with open(analyzer_path, "w") as f:
        analyzer_str = blank_analyzer_template.format(analyzer_name=filename_to_cls(name, suffix="Analyzer"))
        f.write(analyzer_str)


@make.command(help="Generate a observer skeleton")
@click.option("--name", required=True, help="The name of the observer")
@click.option("--line-name", required=True, help="The line name of the observer")
def observer(name, line_name):
    from phitech import const
    from phitech.templates import blank_observer_template

    observer_path = f"{const.BASE_OBSERVERS_PATH}/{name}.py"
    logger.info(f"generate observer -> `{observer_path}`")
    with open(observer_path, "w") as f:
        observer_str = blank_observer_template.format(
            observer_name=filename_to_cls(name, suffix="Observer"), observer_line_name=line_name
        )
        f.write(observer_str)


@make.command(help="Generate a sizer skeleton")
@click.option("--name", required=True, help="The name of the sizer")
@click.option("--line-name", required=True, help="The line name of the sizer")
def sizer(name, line_name):
    from phitech import const
    from phitech.templates import blank_sizer_template

    sizer_path = f"{const.BASE_SIZERS_PATH}/{name}.py"
    logger.info(f"generate sizer -> `{sizer_path}`")
    with open(sizer_path, "w") as f:
        sizer_str = blank_sizer_template.format(sizer_name=filename_to_cls(name, suffix="Sizer"))
        f.write(sizer_str)


@make.command(help="Generate a notebook")
@click.option("--kind", required=True, help="Kind of notebook (explore/strategy)")
@click.option("--name", required=True, help="Name of the notebook")
def notebook(name, kind):
    from phitech.generators.notebook import generate_exploration_notebook, generate_strategy_notebook

    if kind == "explore":
        logger.info(f"generate exploration notebook -> `{name}`")
        generate_exploration_notebook(name)
    elif kind == "strategy":
        logger.info(f"generate notebook for strategy -> `{name}`")
        generate_strategy_notebook(name)


@make.command(help="Generate a bot from `definitions/bots.yml`")
@click.option("--name", required=True, help="The name of the bot")
def bot(name):
    from phitech.generators.bot import generate_bot_directory_structure, generate_bot

    logger.info(f"make directory structure for `{name}`")
    generate_bot_directory_structure(name)
    logger.info("done.")

    logger.info("generate bot")
    generate_bot(name)
    logger.info("done.")


def run():
    cli(prog_name="pt")


if __name__ == "__main__":
    run()
