import pyfolio as pf
import pandas as pd
import matplotlib.pyplot as plt
import backtrader as bt

# TODO: please refactor me


def run_single_strategy_bt(
    instruments,
    strategy_cls,
    starting_cash,
    strategy_params={},
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

    engine.addstrategy(strategy_cls, **strategy_params)
    engine.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    engine.addanalyzer(bt.analyzers.SQN, _name="sqn")
    engine.addanalyzer(bt.analyzers.PyFolio, _name="pyfolio", timeframe=bt.TimeFrame.Days)

    for analyzer_name, (analyzer_cls, kwargs) in analyzers.items():
        engine.addanalyzer(analyzer_cls, _name=analyzer_name, **kwargs)

    for observer_name, (observer_cls, kwargs) in observers.items():
        engine.addobserver(observer_cls, _name=observer_name, **kwargs)

    engine.addsizer(sizer)

    res = engine.run()

    report, perf = make_perf_report(res)
    report["name"] = name
    return res, report, perf[0]["total_value"]


def make_perf_report(strats, logger=None, persist=False, base_path=None):
    if logger:
        logger.info("-" * 30)
        logger.info("REPORT METRICS:")

    report_data = []
    extra = {}
    for idx, strat in enumerate(strats):
        if logger:
            logger.info(f"strat {idx}")

        pfa = strat.analyzers.getbyname("pyfolio")
        returns, positions, transactions, gross_lev = pfa.get_pf_items()
        total_value = positions["first"] + positions.cash
        extra[idx] = {"total_value": total_value, "returns": returns, "positions": positions}

        if logger and len(transactions) == 0:
            logger.info("0 transactions found, nothing to report.")
            continue

        last_account_value = total_value.iloc[-1]
        if logger:
            logger.info(f"last account value -> {last_account_value} $")

        first_account_value = total_value.iloc[0]
        total_return = (last_account_value / first_account_value) - 1
        if logger:
            logger.info(f"total return (pct) -> {total_return*100:.4f} %")

        total_trades = len(transactions)
        if logger:
            logger.info(f"total trades -> {total_trades}")

        sharpe_ratio = strat.analyzers.getbyname("sharpe").get_analysis()["sharperatio"]
        if logger:
            logger.info(f"sharpe ratio -> {sharpe_ratio:.4f}")

        sqn = strat.analyzers.getbyname("sqn").get_analysis()["sqn"]
        if logger:
            logger.info(f"SQN -> {sqn:.4f}")

        report_data.append((idx, total_trades, total_return, sharpe_ratio, sqn))
        if logger:
            logger.info("-" * 30)

    report_df = pd.DataFrame(
        report_data, columns=["strategy_idx", "trades", "total_return", "sharpe_ratio", "sqn"]
    )

    if persist:
        report_df.to_csv(f"{base_path}/report/report.csv", index=False)

    return report_df, extra


def make_plots(strats, logger, base_path=None, show=False):
    for idx, strat in enumerate(strats):
        logger.info(f"strat {idx}")
        logger.info("make plot images")

        pfa = strat.analyzers.getbyname("pyfolio")
        returns, positions, transactions, gross_lev = pfa.get_pf_items()

        if len(transactions) == 0:
            logger.info("0 transactions found, nothing to report.")
            continue

        total_value = positions["first"] + positions.cash

        if show:
            plt.title("Total Value")
            total_value.plot()
            plt.show()
        else:
            total_value.plot().get_figure().savefig(f"{base_path}/report/img/strat{idx}-1-total-value.png")
            plt.figure()

        if show:
            plt.title("Returns")
            returns.plot()
            plt.show()
        else:
            returns.plot().get_figure().savefig(f"{base_path}/report/img/strat{idx}-2-returns.png")
            plt.figure()

        if show:
            pf.plot_annual_returns(returns)
            plt.show()
        else:
            pf.plot_annual_returns(returns).get_figure().savefig(
                f"{base_path}/report/img/strat{idx}-3-returns-annual.png"
            )
            plt.figure()

        if show:
            pf.plot_drawdown_underwater(returns)
            plt.show()
        else:
            pf.plot_drawdown_underwater(returns).get_figure().savefig(
                f"{base_path}/report/img/strat{idx}-4-underwater.png"
            )
            plt.figure()

        if show:
            pf.plot_drawdown_periods(returns)
            plt.show()
        else:
            pf.plot_drawdown_periods(returns).get_figure().savefig(
                f"{base_path}/report/img/strat{idx}-5-drawdown-periods.png"
            )
            plt.figure()

        if show:
            pf.plot_rolling_sharpe(returns)
            plt.show()
        else:
            pf.plot_rolling_sharpe(returns).get_figure().savefig(
                f"{base_path}/report/img/strat{idx}-6-rolling-sharpe.png"
            )
            plt.figure()

        if show:
            pf.plot_daily_volume(returns, transactions)
            plt.show()
        else:
            pf.plot_daily_volume(returns, transactions).get_figure().savefig(
                f"{base_path}/report/img/strat{idx}-7-daily-volume.png"
            )
            plt.figure()

        if show:
            pf.plot_exposures(returns, positions)
            plt.show()
        else:
            pf.plot_exposures(returns, positions).get_figure().savefig(
                f"{base_path}/report/img/strat{idx}-8-long-short-exposure.png"
            )
            plt.figure()

        if show:
            pf.plot_gross_leverage(returns, positions)
            plt.show()
        else:
            pf.plot_gross_leverage(returns, positions).get_figure().savefig(
                f"{base_path}/report/img/strat{idx}-9-gross-leverage.png"
            )
            plt.figure()
