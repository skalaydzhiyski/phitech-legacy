import pyfolio as pf
import pandas as pd
import matplotlib.pyplot as plt


def make_reports(strats, logger, base_path):
    logger.info("REPORT METRICS:")
    report_data = []
    for idx, strat in enumerate(strats):
        logger.info(f"strat {idx}")
        logger.info("-" * 30)

        pfa = strat.analyzers.getbyname("pyfolio")
        returns, positions, transactions, gross_lev = pfa.get_pf_items()

        if len(transactions) == 0:
            logger.info("0 transactions found, nothing to report.")
            continue

        total_value = positions["first"] + positions.cash
        last_account_value = total_value.iloc[-1]
        logger.info(f"last account value -> {last_account_value} $")

        first_account_value = total_value.iloc[0]
        total_return = last_account_value / first_account_value
        logger.info(f"total return (pct) -> {total_return*100-100:.4f} %")

        total_trades = len(transactions)
        logger.info(f"total trades -> {total_trades}")

        sharpe_ratio = strat.analyzers.getbyname("sharpe").get_analysis()["sharperatio"]
        logger.info(f"sharpe ratio -> {sharpe_ratio:.4f}")

        sqn = strat.analyzers.getbyname("sqn").get_analysis()["sqn"]
        logger.info(f"SQN -> {sqn:.4f}")

        report_data.append((idx, total_trades, total_return, sharpe_ratio, sqn))
        logger.info("-" * 30)

        logger.info("plot report -> total value")
        total_value.plot().get_figure().savefig(f"{base_path}/report/img/strat{idx}-1-total-value.png")
        plt.figure()

        logger.info("plot report -> returns")
        returns.plot().get_figure().savefig(f"{base_path}/report/img/strat{idx}-2-returns.png")
        plt.figure()

        logger.info("plot report -> returns annual")
        pf.plot_annual_returns(returns).get_figure().savefig(f"{base_path}/report/img/strat{idx}-3-returns-annual.png")
        plt.figure()

        logger.info("plot report -> underwater")
        pf.plot_drawdown_underwater(returns).get_figure().savefig(f"{base_path}/report/img/strat{idx}-4-underwater.png")
        plt.figure()

        logger.info("plot report -> drawdown periods")
        pf.plot_drawdown_periods(returns).get_figure().savefig(f"{base_path}/report/img/strat{idx}-5-drawdown-periods.png")
        plt.figure()

        logger.info("plot report -> rolling sharpe")
        pf.plot_rolling_sharpe(returns).get_figure().savefig(f"{base_path}/report/img/strat{idx}-6-rolling-sharpe.png")
        plt.figure()

        logger.info("plot report -> daily volume")
        pf.plot_daily_volume(returns, transactions).get_figure().savefig(
            f"{base_path}/report/img/strat{idx}-7-daily-volume.png"
        )
        plt.figure()

        logger.info("plot report -> long/short exposure")
        pf.plot_exposures(returns, positions).get_figure().savefig(
            f"{base_path}/report/img/strat{idx}-8-long-short-exposure.png"
        )
        plt.figure()

        logger.info("plot report -> gross leverage")
        pf.plot_gross_leverage(returns, positions).get_figure().savefig(
            f"{base_path}/report/img/strat{idx}-9-gross-leverage.png"
        )
        logger.info("-" * 30)

    report = pd.DataFrame(
        report_data, columns=["strategy_idx", "trades", "total_return", "sharpe_ratio", "sqn"]
    )
    report.to_csv(f"{base_path}/report/report.csv", index=False)
