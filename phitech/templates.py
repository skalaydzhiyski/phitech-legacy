live_provider_template = """
from atreyu_backtrader_api import IBStore


provider = IBStore(host="{host}", port={port}, clientId={client_id})
"""

backtest_provider_template = """
import phitech.helpers.ib as ib_helper
import tvDatafeed as tvdf


tview = tvdf.TvDatafeed()
provider = ib_helper.get_client(mode="{provider_name}", client_id={client_id})
"""

live_instrument_stock_template = """
instrument_{alias} = provider.getdata(
    name="{ticker}",
    dataname="{ticker}",
    secType="{security_type}",
    exchange="{exchange}",
    currency="USD",
    what="TRADES",
    tradename="{ticker}-{live_type}-{exchange}-USD"
)
instruments.append(("{alias}", bt.TimeFrame.{timeframe}, {compression}, instrument_{alias}))
"""

backtest_tradingview_data_template = """
instrument_{alias} = tview.get_hist(symbol='{symbol}', exchange='{exchange}', n_bars={n_bars}, interval=tvdf.Interval.{interval})
instruments.append(("{alias}", instrument_{alias}))
"""

live_instruments_template = """
from bots.{bot_kind}.{bot_name}.live.provider import provider
import backtrader as bt
from datetime import datetime


instruments = []
{instruments}
"""

backtest_runner_template_new = """
from ip.strategies.{strategy_kind}.{strategy_name} import {strategy_cls}
from ip.analyzers.time_account_value import TimeAccountValue
from ip.analyzers.time_drawdown import TimeDrawdown
from bots.{bot_kind}.{bot_name}.backtest.provider import provider
from logger import logger_main as logger

import phitech.helpers.ib as ib_helper
import phitech.helpers.instruments as instr_helper
import phitech.helpers.backtrader as bt_helper

import pandas as pd


bt_name = "{backtest_name}"
strategy = {strategy_cls}
strategy_conf = {strategy_conf}
sets = instr_helper.get_ticker_strings_for_instruments("{instruments_name}")

report = pd.DataFrame()
perf = {{}}

for idx, ticker_strings in enumerate(sets):
    logger.info(f"running set -> {{idx}}")

    instruments = ib_helper.get_historical_bars_for_ticker_strings(provider, ticker_strings)
    res_, report_, perf_ = bt_helper.run_single_strategy_bt(
        instruments,
        strategy,
        strategy_conf,
        name="{strategy_name}",
        analyzers=dict(time_account_value=(TimeAccountValue, {{}}), time_drawdown=(TimeDrawdown, {{}})),
    )

    report_['bt_name'] = bt_name
    report_["set_id"] = idx
    report = pd.concat([report, report_])

    perf_['bt_name'] = bt_name
    perf_["set_id"] = idx
    perf[idx] = perf_

logger.info('report:')
logger.info(report.T)

report_path = "bots/{bot_kind}/{bot_name}/backtest/report/{backtest_name}_report.csv"
logger.info(f'persist report -> {{report_path}}')
report.to_csv(report_path)

for set_id, perf_ in perf.items():
    perf_path = f"bots/{bot_kind}/{bot_name}/backtest/report/{backtest_name}_set{{set_id}}_perf.csv"
    logger.info(f'persist perf -> {{perf_path}}')
    perf_.to_csv(perf_path)
"""

live_runner_template = """
from ip.strategies.{strategy_kind}.{strategy_name} import {strategy_cls}
from bots.{bot_kind}.{bot_name}.live.instruments import instruments
from bots.{bot_kind}.{bot_name}.live.provider import provider
from logger import logger_main as logger
import backtrader as bt
import time


engine = bt.Cerebro()

broker = provider.getbroker()
engine.setbroker(broker)

for alias, timeframe, compression, instrument in instruments:
	engine.resampledata(instrument, timeframe=timeframe, compression=compression)
	engine.adddata(instrument, name=alias)

strategy_conf = {strategy_config}
engine.addstrategy({strategy_cls}, **strategy_conf)

time.sleep(1)
engine.run()
"""

blank_strategy_template = """
import backtrader as bt
from dotted_dict import DottedDict as dotdict
from logger import logger_main as logger
import datetime
import math


class {strategy_name}(bt.Strategy):
    params = (
        # TODO: add params here
    )

    def __init__(self):
        self.logger = logger.bind(classname=self.__class__.__name__).opt(colors=True)
        self.order = None

        # init datas
        self.t = dotdict(self.dnames)
        self.last_frame = self.datas[0].datetime.datetime(-1)

        # indicators

    def _close_all_open_positions(self):
        self.logger.info("close all open positions")
        for instrument_name, data in self.dnames.items():
            if not self.position:
                continue
            self.logger.info(f'close positions for -> {{instrument_name}}')
            position = self.getposition(data)
            size = -position.size
            if position.size >= 0:
                self.sell(data, size=size)
            else:
                self.buy(data, size=size)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.logger.info("<green>BUY execute</green>")
            else:
                self.logger.info("<red>SELL execute</red>")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.error("Order Rejected!")

        self.order = None

    def notify_trade(self, trade):
        if trade.isopen:
            self.logger.info('<blue>POSITION OPENED</blue>')
        if trade.isclosed:
            self.logger.info('<blue>POSITION CLOSED</blue>')
            self.logger.info(
                f"<yellow>TRADE INFO</blue>: pnl: {{trade.pnl:.2f}}, pnlcomm: {{trade.pnlcomm:.2f}}"
            )
            self.logger.info("*")

    def buy(self, data, size, ticker=""):
        self.logger.info(f"<green>BUY submit</green> ticker: {{ticker}}, size: {{size}}")
        super().buy(data, size=size)

    def sell(self, data, size, ticker=""):
        self.logger.info(f"<red>SELL submit</red> ticker: {{ticker}}, size: {{size}}")
        super().sell(data, size=size)

    def prenext(self):
        pass

    def _check_run_next(self):
        if self.order or self.datas[0].datetime.datetime(0) > self.last_frame:
            return False
        if self.datas[0].datetime.datetime(0) == self.last_frame:
            self._close_all_open_positions()
            return False
        return True

    def next(self):
        # pre
        if not self._check_run_next():
            return

        # logic

    def nextstart(self):
        pass

    def stop(self):
        positions = [self.getposition(v) for _, v in self.t.items()]
        open_positions = [p for p in positions if p.upopened != 0]
        self.logger.info(f'open positions -> {{open_positions}}')
        self.logger.info("STOP")
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

notebook_base_imports = """
import phitech.helpers.ib as ib_helper
import phitech.helpers.instruments as instrument_helper
import phitech.helpers.backtrader as bt_helper
from phitech.generators.helpers import parse_ticker_string

from loguru import logger
logger.disable('__main__')

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

import datetime
import time

plt.style.use('default')
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = .9
plt.rcParams['grid.color'] = 'gray'
plt.rcParams['grid.linewidth'] = .5
plt.rcParams['figure.figsize'] = (9, 5)

if 'client' in locals():
    client.disconnect()
    time.sleep(1)
"""

notebook_client_instance = """
client = ib.get_client(mode="paper_gateway", client_id=3)
client
"""

notebook_ticker_strings = """
ticker_strings = [
    'NVDA.STK.CFD.SMART.1 min|2024-02-01/2024-03-01|first'
]
ticker_strings
"""

notebook_instruments = """
instruments = ib.get_historical_bars_for_ticker_strings(client, ticker_strings)
"""

notebook_single_backtest_runner = """
res, report, perf = bt_helper.run_single_strategy_bt(
    instruments,
    SimpleStrategy, {},
    name="simple",
    analyzers=dict(time_account_value=(TimeAccountValue, {}), time_drawdown=(TimeDrawdown, {}))
)
report
"""

notebook_single_backtest_perf = """
bt_helper.plot_perf(perf)
"""
