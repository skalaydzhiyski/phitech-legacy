from phitech.logger import logger_lib as logger
from phitech.logger import yellow, bold, white, reset, gray, light_gray
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
    from phitech.banner import BANNER
    for line in BANNER.split("\n"):
        logger.info(f" {bold}{white}{line}{reset}")
    logger.info(f"\t    {bold}Phi Technologies.{reset}\n")
    logger.info(f"{yellow}A collection of CLI tools and libraries{reset}")
    logger.info(f"{yellow}to assist the development and deployment{reset}")
    logger.info(f"{yellow}of trading strategies.\n{reset}")


@cli.group("make", help="Generator")
def make():
    pass


@cli.group("rm", help="Remover")
def rm():
    pass


@cli.group("view", help="Viewer")
def view():
    pass


@cli.group("run", help="Runner")
def run():
    pass


@cli.group("export", help="Exporter")
def export():
    pass


@run.command(help="Run a bot backtest or live.")
def ide():
    logger.info("check jupyter and python same path")
    python_path = sp.run(["which", "python"], capture_output=True, text=True).stdout.strip()
    jupyter_path = sp.run(["which", "python"], capture_output=True, text=True).stdout.strip()
    assert python_path.split("/")[:-1] == jupyter_path.split("/")[:-1]
    logger.info("running jupyter lab")
    os.system("jupyter lab .")


@view.command(help="View reports for a backktest set")
@click.option("--bot", required=True, help="The name of the bot")
@click.option("--bt", required=True, help="The name of the backtest")
@click.option("--sid", required=True, help="The id of the set")
def report(bot, bt, sid):
    from phitech import conf, const
    from PIL import Image
    from fpdf import FPDF

    logger.info(f"view report -> bot: {bot}, backtest: {bt}, set: {set}")

    kind = conf.bots[bot].kind
    base_img_path = f"{const.BASE_BOTS_PATH}/{kind}/{bot}/backtest/{bt}/sets/set_{sid}/report/img"
    try:
        os.system(f"open {base_img_path}/*.png")
    except Exception as e:
        logger.errror(e)
        logger.info("Currently only works on MacOS. TODO: make it work for linux as well")


@rm.command(help="Remove a bot")
@click.option("--name", required=True, help="The name of the bot")
def bot(name):
    from phitech import conf

    kind = conf.bots[name].kind
    logger.info(f"remove -> bots/{kind}/{name}")
    os.system(f"rm -rf ./bots/{kind}/{name}")
    if len(os.listdir(f"./bots/{kind}")) == 0:
        logger.info("empty kind, remove")
        os.system(f"rm -rf ./bots/{kind}")


@run.command(help="Run a bot backtest or live.")
@click.option("--name", required=True, help="The name of the bot")
@click.option("--backtest", required=False, help="The comma separated list of backtests to run.")
@click.option("--live", is_flag=True, required=False, help="Run the bot live")
def bot(name, backtest=None, live=False):
    from phitech import conf

    logger.info("boot engine")
    # os.system("pt info")

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
            backtest_runner = f"bots/{bot_def.kind}/{name}/backtest/{bt_name}/runner.py"
            os.system(f"python {backtest_runner}")
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
    from phitech.generators.helpers import filename_to_cls
    from phitech import const
    from phitech.templates import (
        blank_strategy_template,
    )

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
    from phitech.generators.helpers import filename_to_cls
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
    from phitech.generators.helpers import filename_to_cls
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
    from phitech.generators.helpers import filename_to_cls
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
    from phitech.generators.helpers import filename_to_cls
    from phitech import const
    from phitech.templates import blank_sizer_template

    sizer_path = f"{const.BASE_SIZERS_PATH}/{name}.py"
    logger.info(f"generate sizer -> `{sizer_path}`")
    with open(sizer_path, "w") as f:
        sizer_str = blank_sizer_template.format(sizer_name=filename_to_cls(name, suffix="Sizer"))
        f.write(sizer_str)


@make.command(help="Generate instruments")
@click.option("--name", required=True, help="The name of the instruments definition")
def instruments(name):
    from phitech.helpers.instruments import make_ticker_strings, make_instruments_definition
    tickers = input("tickers [a,b|c,d|...]: ")
    tickers = [t.strip().upper() for t in tickers.split("|")]
    tickers = [[t_.strip() for t_ in t.split(",")] for t in tickers]
    aliases = [t.strip().lower() for t in tickers[0]]

    timeframes = input("timeframes [a,b,..]: ")
    timeframes = [tf.strip() for tf in timeframes.split(',')]
    if len(timeframes) == 1:
        timeframes *= len(tickers[0])

    aliases = input("aliases [a,b,..]: ")
    if len(aliases.strip()) != 0:
        aliases = [a.strip() for a in aliases.split(',')]
    else:
        aliases = [t.lower() for t in tickers[0]]

    underlying_type = input("underlying type: ").strip().upper()
    live_type = input("live type: ").strip().upper()

    ranges = input("ranges [l/r|..]: ")
    ranges = [r.strip().split('/') for r in ranges.split("|")]

    ticker_strings = make_ticker_strings(
        tickers, underlying_type, live_type, timeframes, aliases, ranges
    )
    make_instruments_definition(name, ticker_strings)


@make.command(help="Generate a notebook")
@click.option("--name", required=True, help="Name of the notebook")
@click.option("--kind", required=True, help="Kind of notebook (explore/strategy)")
@click.option("--instruments", required=False, help="Instruments to load")
def notebook(name, kind, instruments):
    from phitech.generators.notebook import generate_exploration_notebook, generate_strategy_notebook

    if kind == "explore":
        logger.info(f"generate exploration notebook -> `{name}`")
        generate_exploration_notebook(name, instruments)

    elif kind == "strategy":
        logger.info(f"generate strategy notebook -> `{name}`")
        strategy_kind = input("strategy kind (string): ")
        generate_strategy_notebook(name, instruments, strategy_kind)


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


@export.command(help="View reports for a backktest set")
@click.option("--account", required=True, help="The name of the bot")
@click.option("--path", required=True, help="The name of the bot")
def trades(account, path):
    import phitech.helpers.ib as ib_helper
    import pandas as pd
    import datetime

    client = ib_helper.get_client(mode=f"{account}_workstation", client_id=127123)
    logger.info(f'client -> {client}')
    logger.info(f"get trades for account -> `{account}`")
    logger.info(f'path -> {path}')

    trades = ib_helper.get_trades(client)
    trades.drop(columns=["execId"])
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    if trades.shape[0] == 0:
        logger.info("no trades found.")
        return

    trades.to_csv(f"{path}/trades_{today}.csv", index=False)
    logger.info('done.')
    client.disconnect()


def run():
    cli(prog_name="pt")


if __name__ == "__main__":
    run()
