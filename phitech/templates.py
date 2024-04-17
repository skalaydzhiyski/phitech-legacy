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
from ip.analyzers.position_returns import PositionReturnsAnalyzer
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
    btest = bt_helper.run_single_strategy_bt(
        instruments,
        strategy,
        strategy_conf,
        name="{strategy_name}",
        analyzers=dict(time_account_value=(TimeAccountValue, {{}}), time_drawdown=(TimeDrawdown, {{}}), position_returns=(PositionReturnsAnalyzer, {{}})),
    )

    btest['report']['bt_name'] = bt_name
    btest['report']["set_id"] = idx
    report = pd.concat([report, btest['report']])

    btest['perf']['bt_name'] = bt_name
    btest['perf']["set_id"] = idx
    perf[idx] = btest['perf']

report_path = "bots/{bot_kind}/{bot_name}/backtest/report/{backtest_name}_report.csv"
logger.info(f'persist report -> {{report_path}}')
report.to_csv(report_path, index=False)

for set_id, perf_ in perf.items():
    perf_path = f"bots/{bot_kind}/{bot_name}/backtest/report/{backtest_name}_set{{set_id}}_perf.csv"
    logger.info(f'persist perf -> {{perf_path}}')
    perf_.to_csv(perf_path, index=False)

logger.info('report:')
logger.info(report.T)
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
from logger import logger_main
from logger import (
    red,
    light_red,
    green,
    light_green,
    yellow,
    light_yellow,
    bold,
    reset,
)
import datetime
import math
from collections import defaultdict


class {strategy_name}(bt.Strategy):
    params = (("period", 10),)

    def __init__(self):
        self.logger = logger_main
        self.orders = {{}}

        # init datas
        self.t = dotdict(self.dnames)

        # indicators

        # extra

    def notify_order(self, order):
        if order.status in [order.Submitted]:
            return

        if order.status in [order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.logger.info(f"{{light_green}}BUY execute {{reset}}dname: {{bold}}{{order.data._name}}{{reset}}")
            else:
                self.logger.info(f"{{light_red}}SELL execute {{reset}}dname: {{bold}}{{order.data._name}}{{reset}}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.error("Order Rejected!")

        self.orders = {{i: o for i, o in self.orders.items() if o.ref != order.ref}}

    def notify_trade(self, trade):
        if trade.isopen:
            self.logger.info(f"{{yellow}}POSITION OPENED{{reset}}")
        if trade.isclosed:
            self.logger.info(f"{{yellow}}POSITION CLOSED{{reset}}")
            self.logger.info(
                f"{{light_yellow}}TRADE INFO{{reset}}: dname: {{bold}}{{trade.getdataname()}}{{reset}}, pnl: {{trade.pnl:.2f}}, pnlcomm: {{trade.pnlcomm:.2f}}"
            )

    def buy(self, data, size):
        self.logger.info(f"{{green}}BUY submit{{reset}} ticker: {{bold}}{{data._name}}{{reset}}, size: {{size}}")
        order = super().buy(data, size=size)
        self.orders[data._name] = order
        return order

    def sell(self, data, size):
        self.logger.info(f"{{red}}SELL submit{{reset}} ticker: {{bold}}{{data._name}}{{reset}}, size: {{size}}")
        order = super().sell(data, size=size)
        self.orders[data._name] = order
        return order

    def prenext(self):
        pass

    def next(self):
        pass

    def nextstart(self):
        pass

    def _view_open_positions(self):
        open_positions = self._get_all_open_positions()
        if len(open_positions) == 0:
            return
        msg = ", ".join(
            [f"{{instrument._name}}: {{position.size}}" for instrument, position in open_positions.items()]
        )
        self.logger.info(msg)

    def _no_open_orders(self, instrument):
        return instrument not in self.orders

    def _get_position_for(self, instrument):
        positions = self._get_all_positions()
        if instrument in positions:
            return positions[instrument]

    def _get_open_position_for(self, instrument):
        open_positions = self._get_all_open_positions()
        if instrument in open_positions:
            return open_positions[instrument]

    def _get_all_positions(self):
        return {{instr: self.getposition(instr) for instr in self.t.values()}}

    def _get_all_open_positions(self):
        return {{i: p for i, p in self._get_all_positions().items() if p.size != 0}}

    def _close_all_open_positions(self):
        self.logger.info("close all open positions")
        for instrument, position in self._get_all_open_positions().items():
            self.close(instrument, position.size)

    def stop(self):
        positions = [self.getposition(v) for _, v in self.t.items()]
        open_positions = [p for p in positions if p.upopened != 0]
        self.logger.info(f"open positions -> {{open_positions}}")
        if len(open_positions) != 0:
            self.logger.warning("WARNING: positions still open")
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
from ip.analyzers.time_account_value import TimeAccountValue
from ip.analyzers.time_drawdown import TimeDrawdown
import phitech.helpers.ib as ib_helper
import phitech.helpers.instruments as instr_helper
import phitech.helpers.backtrader as bt_helper
import phitech.tradingview.helpers as tview_helper
from phitech.generators.helpers import parse_ticker_string

import logging
logging.getLogger('phitech').setLevel(logging.ERROR)

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
client = ib_helper.get_client(mode="paper_gateway", client_id=3)
client
"""

notebook_ticker_strings = """
ticker_strings = instr_helper.get_ticker_strings_for_instruments("{instruments_name}")
ticker_strings
"""

notebook_scanner = """
tickers = tview_helper.get_scanner_data(
    Query()
        .select('name', 'exchange')
        .where(
            Column('exchange').isin(['NASDAQ', 'NYSE']),
        )
)
tickers
"""

notebook_custom_ticker_strings = """
ticker_strings = [
	# TODO: build a list of tickers here
]
set_id = 0
tickers = ticker_strings[set_id]
"""

notebook_instruments = """

instruments = ib_helper.get_historical_bars_for_ticker_strings(client, tickers)
"""

notebook_single_backtest_runner = """
import logging
logger_main.setLevel(logging.WARNING)

btest = bt_helper.run_single_strategy_bt(
    instruments,
    {strategy_cls}, {strategy_config},
    name="simple",
    analyzers=dict(time_account_value=(TimeAccountValue, {{}}), time_drawdown=(TimeDrawdown, {{}}))
)
btest['report']
"""

notebook_single_backtest_perf = """
bt_helper.plot_perf(btest['perf'])
"""

sierra_study_base_script_template = """
#include <string>

#include "sierrachart.h"

SCDLLName("Basic_Trend_System");

// global
const float marker_offset = 0.05;

// helpers
void send_buy_order(int size, bool direction, SCStudyInterfaceRef& sc,
                    SCSubgraphRef& sg_buy_entry, SCSubgraphRef& sg_buy_exit) {{
  s_SCNewOrder order;
  order.OrderQuantity = size;
  order.OrderType = SCT_ORDERTYPE_MARKET;
  order.TimeInForce = SCT_TIF_DAY;
  int res = 0;
  int internal_order_id = 0;
  if (direction) {{
    res = static_cast<int>(sc.BuyEntry(order));
    if (res) {{
      sc.AddMessageToLog("BUY enter", 0);
      sg_buy_entry[sc.Index] = sc.Low[sc.Index] - marker_offset;
      internal_order_id = order.InternalOrderID;
    }}
  }} else {{
    res = static_cast<int>(sc.BuyExit(order));
    if (res) {{
      sc.AddMessageToLog("BUY exit", 0);
      sg_buy_exit[sc.Index] = sc.High[sc.Index] + marker_offset;
      internal_order_id = order.InternalOrderID;
    }}
  }}
  sc.SetPersistentInt(0, internal_order_id);
}}

void send_sell_order(int size, bool direction, SCStudyInterfaceRef& sc,
                     SCSubgraphRef& sg_sell_entry,
                     SCSubgraphRef& sg_sell_exit) {{
  s_SCNewOrder order;
  order.OrderQuantity = size;
  order.OrderType = SCT_ORDERTYPE_MARKET;
  order.TimeInForce = SCT_TIF_DAY;
  int res = 0;
  int internal_order_id = 0;
  if (direction) {{
    res = static_cast<int>(sc.SellEntry(order));
    if (res) {{
      sc.AddMessageToLog("SELL enter", 0);
      sg_sell_entry[sc.Index] = sc.High[sc.Index] + marker_offset;
      internal_order_id = order.InternalOrderID;
    }}
  }} else {{
    res = static_cast<int>(sc.SellExit(order));
    if (res) {{
      sc.AddMessageToLog("SELL exit", 0);
      sg_sell_exit[sc.Index] = sc.Low[sc.Index] - marker_offset;
      internal_order_id = order.InternalOrderID;
    }}
  }}
  sc.SetPersistentInt(0, internal_order_id);
}}

SCSFExport scsf_{func_name}(SCStudyInterfaceRef sc) {{
  // markers
  SCSubgraphRef sg_buy_entry = sc.Subgraph[0];
  SCSubgraphRef sg_buy_exit = sc.Subgraph[1];
  SCSubgraphRef sg_sell_entry = sc.Subgraph[2];
  SCSubgraphRef sg_sell_exit = sc.Subgraph[3];

  // extra subgraphs

  // inputs
  SCInputRef i_enabled = sc.Input[0];
  SCInputRef i_size = sc.Input[2];
  SCInputRef i_send_trades = sc.Input[3];

  if (sc.SetDefaults) {{
    sc.GraphName = "Basic Trend System";

    // markers
    sg_buy_entry.Name = "Buy Entry";
    sg_buy_entry.DrawStyle = DRAWSTYLE_ARROW_UP;
    sg_buy_entry.PrimaryColor = RGB(0, 145, 0);
    sg_buy_entry.LineWidth = 2;
    sg_buy_entry.DrawZeros = false;

    sg_buy_exit.Name = "Buy Exit";
    sg_buy_exit.DrawStyle = DRAWSTYLE_ARROW_DOWN;
    sg_buy_exit.PrimaryColor = RGB(145, 0, 0);
    sg_buy_exit.LineWidth = 2;
    sg_buy_exit.DrawZeros = false;

    sg_sell_entry.Name = "Sell Entry";
    sg_sell_entry.DrawStyle = DRAWSTYLE_ARROW_DOWN;
    sg_sell_entry.PrimaryColor = RGB(145, 0, 0);
    sg_sell_entry.LineWidth = 2;
    sg_sell_entry.DrawZeros = false;

    sg_sell_exit.Name = "Sell Exit";
    sg_sell_exit.DrawStyle = DRAWSTYLE_ARROW_UP;
    sg_sell_exit.PrimaryColor = RGB(0, 145, 0);
    sg_sell_exit.LineWidth = 2;
    sg_sell_exit.DrawZeros = false;

    // subgraphs

    // inputs
    i_enabled.Name = "Enabled";
    i_enabled.SetYesNo(1);

    i_size.Name = "Size";
    i_size.SetInt(10);

    i_send_trades.Name = "Send Orders to Broker";
    i_send_trades.SetYesNo(1);

    // settings
    sc.AutoLoop = 1;
    sc.GraphRegion = 0;
    sc.AllowMultipleEntriesInSameDirection = false;
    sc.MaximumPositionAllowed = 100;
    sc.SupportReversals = false;
    sc.AllowOppositeEntryWithOpposingPositionOrOrders = false;
    sc.SupportAttachedOrdersForTrading = false;
    sc.CancelAllOrdersOnEntriesAndReversals = true;
    sc.AllowEntryWithWorkingOrders = false;
    sc.CancelAllWorkingOrdersOnExit = false;
    sc.AllowOnlyOneTradePerBar = true;
    sc.MaintainTradeStatisticsAndTradesData = true;
    return;
  }}

  // pre
  if (!i_enabled.GetYesNo()) return;
  if (sc.IsFullRecalculation) return;

  sc.SendOrdersToTradeService = i_send_trades.GetYesNo();
  s_SCPositionData position;
  sc.GetTradePosition(position);

  auto buy = [&sc, &sg_buy_entry, &sg_sell_entry](int size, bool direction) {{
    return send_buy_order(size, direction, sc, sg_buy_entry, sg_sell_entry);
  }};
  auto sell = [&sc, &sg_sell_entry, &sg_sell_exit](int size, bool direction) {{
    return send_sell_order(size, direction, sc, sg_sell_entry, sg_sell_exit);
  }};

  // system
  int size = i_size.GetInt();
  int internal_order_id = sc.GetPersistentInt(0);

  // TODO: system logic here
}}
"""

sierra_study_compile_commands_template = """
[
  {{
    "directory": "{sierra_chart_base_dir}",
    "command": "/usr/bin/x86_64-w64-mingw32-g++ -I /usr/include/c++/11 -I /usr/include/x86_64-linux-gnu/c++/11 -I {sierra_chart_base_dir} -w -s -O2 -m64 -march=native -static -shared {study_name}.cpp -o simple_study_64.dll",
    "file": "{study_name}.cpp"
  }}
]
"""

sierra_study_build_script_template = """
#!/bin/bash
name="{study_name}"
base_sierra_dir="{sierra_chart_base_dir}"

echo "compile shared library"
/usr/bin/x86_64-w64-mingw32-g++ -Wall -I $base_sierra_dir/ACS_Source -w -s -O2 -m64 -march=native -static -shared $name.cpp -o $name.dll

SC_UDP_PORT=8898
WIN_FP=C:\\\\SierraChart\\Data\\\\$name.dll
RLEASE_DLL_CMD=RELEASE_DLL--$WIN_FP
RLOAD_DLL_CMD=ALLOW_LOAD_DLL--$WIN_FP

echo "deploy to sierra"
echo "release lib"
echo $RLEASE_DLL_CMD
echo -n $RLEASE_DLL_CMD > /dev/udp/127.0.0.1/$SC_UDP_PORT
sleep 2

echo "copy .dll file to Data/"
mv $name.dll $base_sierra_dir/Data/

echo "reload lib"
echo $RLOAD_DLL_CMD
echo -n $RLOAD_DLL_CMD > /dev/udp/127.0.0.1/$SC_UDP_PORT

echo "copy study to $PYTHONPATH project"
cp $name.cpp $PYTHONPATH/ip/sierra-studies/
echo "done."
"""
