provider_template = """
from atreyu_backtrader_api import IBStore


provider = IBStore(host="{host}", port={port}, clientId={client_id})
"""

backtest_instrument_stock_template = """
instrument_{ticker} = provider.getdata(
    name="{ticker}",
    dataname="{ticker}",
    secType="{security_type}",
    exchange="{exchange}",
    currency="USD", 
    what="TRADES",
    historical=True,
    fromdate=date.fromisoformat("{from_date}"),
    todate=date.fromisoformat("{to_date}"),
    rtbar=True,
)
instruments.append(instrument_{ticker})
"""

instruments_template = """
from bots.{bot_kind}.{bot_name}.backtest.{backtest_name}.provider import provider
from datetime import date


instruments = []
{instruments}
"""

strategy_import_template = """
from ip.strategies.{strategy_kind}.{strategy_name} import {strategy_cls}
"""

strategy_template = """
strategy_config = {strategy_config}
strategies.append(({strategy_cls}, strategy_config))
"""

strategies_template = """
{strategy_imports}

strategies = []
{strategies}
"""

backtest_runner_template = """
from bots.{bot_kind}.{bot_name}.backtest.{backtest_name}.instruments import instruments
from bots.{bot_kind}.{bot_name}.backtest.{backtest_name}.strategies import strategies
from logger import logger
import backtrader as bt
import time


engine = bt.Cerebro()

for instrument in instruments:
	engine.resampledata(instrument, timeframe=bt.TimeFrame.{timeframe}, compression={compression})
	engine.adddata(instrument)

for strategy, config in strategies:
	engine.addstrategy(strategy, **config)

logger.info("sleep for 1 second to allow for smooth boot")
time.sleep(1)
engine.run()
"""

blank_strategy_template = """
"""
blank_indicator_template = """
"""

blank_analyzer_template = """
"""

blank_observer_template = """
"""

blank_sizer_template = """
"""
