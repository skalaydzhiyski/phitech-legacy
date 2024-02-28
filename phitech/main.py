from phitech.logger import logger
from phitech.banner import BANNER
import click

import os
import sys
import yaml
import subprocess as sp


@click.group("cli")
def cli():
    pass


@cli.command("info")
def info():
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
    bot_def = conf.bots[name]
    if live:
        logger.info(f"start live execution of -> `{name}`")
        live_run_cmd = f"python3 bots/{bot_def.kind}/{name}/live/runner.py"
        os.system(live_run_cmd)
    else:
        logger.info(f"start backtest for -> `{name}`")
        backtests = backtest.split(",")
        for bt_name in backtests:
            logger.info(f"running backtest -> `{bt_name}`")
            bt_run_cmd = f"python3 bots/{bot_def.kind}/{name}/backtest/{bt_name}/runner.py"
            os.system(bt_run_cmd)
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
def strategy(name):
    from phitech import const
    from phitech.templates import blank_strategy_template
    strategy_path = f"{const.BASE_STRATEGIES_PATH}/{name}.py"
    logger.info(f"generate strategy -> `{strategy_path}`")
    with open(strategy_path, "w") as f:
        f.write(blank_strategy_template.format(strategy_name=name))


@make.command(help="Generate a indicator skeleton")
@click.option("--name", required=True, help="The name of the indicator")
def indicator(name):
    from phitech import const
    from phitech.templates import blank_indicator_template
    indicator_path = f"{const.BASE_INDICATORS_PATH}/{name}.py"
    logger.info(f"generate indicator -> `{indicator_path}`")
    with open(indicator_path, "w") as f:
        f.write(blank_indicator_template.format(indicator_name=name))


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

    logger.info("generate bot")
    generate_bot(name)


def run():
    cli(prog_name="pt")


if __name__ == "__main__":
    run()
