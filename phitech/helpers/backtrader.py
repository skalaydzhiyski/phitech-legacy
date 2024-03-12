import pandas as pd
import matplotlib.pyplot as plt
import backtrader as bt
from dotted_dict import DottedDict as dotdict

# TODO: please refactor me


def run_single_strategy_bt(
    instruments,
    strategy_cls,
    strategy_params={},
    starting_cash=1000000,
    name="",
    observers={},
    analyzers={},
    sizer=None,
    plot=True,
):
    engine = bt.Cerebro()
    engine.broker.setcash(starting_cash)

    for instrument_alias, instrument in instruments.items():
        engine.adddata(bt.feeds.PandasData(dataname=instrument), name=instrument_alias)

    engine.addanalyzer(bt.analyzers.SharpeRatio, _name="stat_sharpe")
    engine.addanalyzer(bt.analyzers.SQN, _name="stat_sqn")
    engine.addanalyzer(bt.analyzers.TradeAnalyzer, _name="stat_trade_analyzer")
    engine.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")

    for analyzer_name, (analyzer_cls, kwargs) in analyzers.items():
        engine.addanalyzer(analyzer_cls, _name=analyzer_name, **kwargs)

    for observer_name, (observer_cls, kwargs) in observers.items():
        engine.addobserver(observer_cls, _name=observer_name, **kwargs)

    engine.addsizer(sizer)

    engine.addstrategy(strategy_cls, **strategy_params)

    res = engine.run()

    report, perf, daily_returns = make_perf_report_single_strategy(res[0])
    report["name"] = name
    perf['name'] = name
    return res, report, perf


def make_perf_report_single_strategy(strat, name=""):
    time_account_value = pd.DataFrame(
        strat.analyzers.getbyname('time_account_value').get_analysis()['account_value'],
        columns=['dt', 'cash', 'total_value', 'pct_of_starting']
    ).set_index('dt')
    time_account_value.index = pd.to_datetime(time_account_value.index)

    time_returns = pd.DataFrame(
        strat.analyzers.getbyname('time_return').get_analysis().items(),
        columns=['dt', 'returns']
    ).set_index('dt')
    time_returns.index = pd.to_datetime(time_returns.index)

    time_drawdown = pd.DataFrame(
        strat.analyzers.getbyname('time_drawdown').get_analysis()['drawdown'],
        columns=['dt', 'drawdown']
    ).set_index('dt')
    time_drawdown.index = pd.to_datetime(time_drawdown.index)

    total_return = time_account_value.pct_of_starting[-1] - 1
    sharpe_ratio = strat.analyzers.getbyname('stat_sharpe').get_analysis()['sharperatio']
    stat_sqn = strat.analyzers.getbyname('stat_sqn').get_analysis()['sqn']
    max_drawdown = time_drawdown.drawdown.min()

    trade_analyzer_stats = strat.analyzers.getbyname('stat_trade_analyzer').get_analysis()
    total_closed_trades = trade_analyzer_stats['total']['closed']
    streak_won_longest = trade_analyzer_stats['streak']['won']['longest']
    streak_lost_longest = trade_analyzer_stats['streak']['lost']['longest']
    total_time_in_market = trade_analyzer_stats['len']['total']
    max_time_in_market = trade_analyzer_stats['len']['max']
    min_time_in_market = trade_analyzer_stats['len']['min']
    avg_time_in_market = trade_analyzer_stats['len']['average']
    avg_time_in_market_won = trade_analyzer_stats['len']['won']['average']
    avg_time_in_market_lost = trade_analyzer_stats['len']['lost']['average']

    report = pd.DataFrame(
        [(total_return, sharpe_ratio, stat_sqn, max_drawdown, total_closed_trades, streak_won_longest, streak_lost_longest, total_time_in_market, max_time_in_market, min_time_in_market, avg_time_in_market, avg_time_in_market_won, avg_time_in_market_lost)],
        columns=['total_return', 'sharpe_ratio', 'stat_sqn', 'max_drawdown', 'total_closed_trades', 'streak_won_longest', 'streak_lost_longest', 'total_time_in_market', 'max_time_in_market', 'min_time_in_market', 'avg_time_in_market', 'avg_time_in_market_won', 'avg_time_in_market_lost']
    )

    perf = pd.concat(
        [time_account_value, time_drawdown],
        axis=1
    )
    return report, perf, time_returns
