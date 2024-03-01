live_provider_template = """
from atreyu_backtrader_api import IBStore


provider = IBStore(host="{host}", port={port}, clientId={client_id})
"""

backtest_provider_template = """
import phitech.helpers.ib as ib
from logger import logger


provider = ib.get_client(mode="{provider_name}", client_id={client_id})
logger.info(provider)
"""

live_instrument_stock_template = """
instrument_{alias} = provider.getdata(
    name="{ticker}",
    dataname="{ticker}",
    secType="{security_type}",
    exchange="{exchange}",
    currency="USD", 
    what="TRADES",
    timeframe=bt.TimeFrame.{timeframe},
    compression={compression},
    tradename="{ticker}-{live_type}-{exchange}-USD"
)
instruments.append(("{alias}", instrument_{alias}))
"""

backtest_instrument_stock_template = """
contract = Contract(secType="{underlying_type}", symbol="{ticker}", exchange="{exchange}", currency='USD')
provider.qualifyContracts(contract)
instrument_{alias} = ib.get_historical_bars(
	provider, contract, "{start_date}", "{end_date}", "{interval}"
)
instruments.append(("{alias}", instrument_{alias}))
"""

live_instruments_template = """
from bots.{bot_kind}.{bot_name}.live.provider import provider
import backtrader as bt
from datetime import datetime


instruments = []
{instruments}
"""

backtest_instruments_template = """
from bots.{bot_kind}.{bot_name}.backtest.{backtest_name}.provider import provider
import phitech.helpers.ib as ib
from ib_insync.contract import Contract
import backtrader as bt
from datetime import datetime


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
from bots.{bot_kind}.{bot_name}.backtest.{backtest_name}.sets.set_{set_idx}.instruments import instruments
from bots.{bot_kind}.{bot_name}.backtest.{backtest_name}.strategies import strategies
from logger import logger
import backtrader as bt
import time


engine = bt.Cerebro()

for alias, instrument in instruments:
	data = bt.feeds.PandasData(dataname=instrument)
	engine.adddata(data, name=alias)

for strategy, config in strategies:
	engine.addstrategy(strategy, **config)

time.sleep(1)
engine.run()
"""

live_runner_template = """
from bots.{bot_kind}.{bot_name}.live.instruments import instruments
from bots.{bot_kind}.{bot_name}.live.strategies import strategies
from logger import logger
import backtrader as bt
import time


engine = bt.Cerebro()

for alias, instrument in instruments:
	engine.adddata(instrument, name=alias)

for strategy, config in strategies:
	engine.addstrategy(strategy, **config)

time.sleep(1)
engine.run()
"""

blank_strategy_template = """
import backtrader as bt
from dotted_dict import DottedDict as dotdict
from logger import logger


class {strategy_name}(bt.Strategy):
    params = (
    	# TODO: add params here. Ex -> ('period', 12)
    )

    def __init__(self):
        # init datas
        self.t = dotdict(self.dnames)

        # indicators

    def notify_order(self, order):
        # Notification about order status changes
        pass  

    def notify_trade(self, trade):
        # Notification about trade updates
        pass  

    def prenext(self):
        # Actions before the actual 'next' call
        pass 

    def next(self):
        # Main trading logic goes here
        pass

    def nextstart(self):
        # Actions to be performed specifically 
        # at the start of a new "next" cycle
        pass

    def stop(self):
        # Actions to perform at the end (could be used for reporting)
        pass
"""
blank_indicator_template = """
import backtrader as bt


class {indicator_name}(bt.Indicator):
    lines = ('{indicator_line_name}',)  # Name(s) of the indicator output line(s)
    params = (
    	# TODO: add params here. Ex -> ('period', 12)
    )

    def __init__(self):
        # Add other lines or initialization logic here
        pass

    def once(self, start, end):
        # Called once to prepare for calculations 
        # (happens at the very beginning of the backtest)
        pass

    def prenext(self):
        # Called right before the 'next' method 
        pass

    def next(self):
        # Where the core calculation logic of the indicator goes
        pass

    def nextstart(self):
        # Called similarly to the strategy's nextstart 
        # but at the indicator level
        pass
"""

blank_analyzer_template = """
import backtrader as bt


class {analyzer_name}(bt.Analyzer):
    def __init__(self):
        # Initialize any internal variables needed for analysis
        pass

    def start(self):
        # Called at the start of the backtest (initialization)
        pass

    def prenext(self):
        # Called before the strategy's `next` method
        pass

    def next(self):
        # Gather information/update calculations during bar cycles
        pass

    def notify_order(self, order):
        # Optionally react to order updates
        pass

    def notify_trade(self, trade):
        # Optionally react to trade updates
        pass

    def stop(self):
        # Called at the end - finalize calculations and generate output
        pass

    def get_analysis(self):
        # Return the results of the analysis in a structured format
        # (dict, pandas Series, etc.)
        pass
"""

blank_observer_template = """
import backtrader as bt


class {observer_name}(bt.Observer):
    lines = ('{observer_line_name}',)  # Names of output lines plotted by the observer
    plotinfo = dict(plot=True, subplot=False)  # Plotting config (defaults are fine)
    params = (
    	# TODO: add params here. Ex -> ('period', 12)
    )

    def __init__(self):
        # Example: Store a moving average for tracking
        pass

    def next(self):
        # Called at the end of each bar cycle. Observe values, plot, etc.
        pass
"""

blank_sizer_template = """
import backtrader as bt


class {sizer_name}(bt.Sizer):
    params = (
    	# TODO: add params here. Ex -> ('period', 12)
    )

    def __init__(self):
        # Optional initialization
        pass

    def _getsizing(self, comminfo, cash, data, isbuy):
        # Calculate and return the sizing for the order
        # EX: size = cash / data.close[0] * (self.params.stake / 100)
        return 1
"""
