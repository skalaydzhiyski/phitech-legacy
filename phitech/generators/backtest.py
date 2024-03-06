from phitech import conf, const
from phitech.logger import logger
from phitech.generators.helpers import (
    write_to_file,
    filename_to_cls,
    parse_ticker_string,
    parse_sets_string,
    parse_tradingview_ticker_string,
)
from phitech.templates import (
    backtest_provider_template,
    backtest_instruments_template,
    backtest_instrument_stock_template,
    strategy_import_template,
    strategy_template,
    strategies_template,
    analyzer_template,
    backtest_runner_template,
    backtest_tradingview_data_template,
)


def generate_backtest_provider(backtest_def):
    provider_def = conf.providers[backtest_def.provider]
    return backtest_provider_template.format(
        provider_name=backtest_def.provider,
        client_id=backtest_def.broker.client_id,
    )


def generate_backtest_instruments(tickers, bot_kind, bot_name, backtest_name):
    instrument_strings = []
    for ticker_str in tickers:
        istr = ""
        if ticker_str.startswith("tradingview"):
            logger.info("tradingview request in instruments")
            symbol, exchange, n_bars, interval, alias = parse_tradingview_ticker_string(ticker_str)
            istr = backtest_tradingview_data_template.format(
                symbol=symbol,
                exchange=exchange,
                n_bars=n_bars,
                interval=interval,
                alias=alias,
            )
        else:
            (
                ticker,
                underlying_type,
                _,
                exchange,
                interval,
                alias,
                start_date,
                end_date,
            ) = parse_ticker_string(ticker_str)
            if underlying_type == "STK":
                istr = backtest_instrument_stock_template.format(
                    ticker=ticker,
                    underlying_type=underlying_type,
                    exchange=exchange,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date,
                    alias=alias,
                )
            else:
                raise NotImplementedError("not ready yet")
        instrument_strings.append(istr)

    instruments_str = "".join(instrument_strings)
    return backtest_instruments_template.format(
        bot_kind=bot_kind, bot_name=bot_name, backtest_name=backtest_name, instruments=instruments_str
    )


def generate_backtest_strategies(bot_def):
    strategy_imports = "\n".join(
        [
            strategy_import_template.format(
                strategy_kind=sdef.kind,
                strategy_name=sdef.name,
                strategy_cls=filename_to_cls(sdef.name),
            ).strip()
            for sdef in bot_def.strategies
        ]
    )
    strategies = "".join(
        [
            strategy_template.format(
                strategy_cls=filename_to_cls(sdef.name),
                strategy_config=conf.strategy_configs[sdef.config].config.to_dict(),
            )
            for sdef in bot_def.strategies
        ]
    )
    return strategies_template.format(
        strategy_imports=strategy_imports,
        strategies=strategies,
    )


def generate_backtest(backtest_name, bot_name, bot_def):
    backtest_def = conf.backtests[backtest_name]
    base_backtest_path = f"bots/{bot_def.kind}/{bot_name}/backtest/{backtest_name}"

    logger.info("generate backtest provider")
    backtest_provider_str = generate_backtest_provider(backtest_def)
    write_to_file(backtest_provider_str, f"{base_backtest_path}/provider.py")

    logger.info("generate backtest instruments")
    set_idxs = parse_sets_string(
        backtest_def.universe.instruments.sets,
        name=backtest_def.universe.instruments.name,
    )
    for idx, sdef in enumerate(conf.instruments[backtest_def.universe.instruments.name].sets):
        if idx not in set_idxs:
            continue

        logger.info(f"generate instruments for set -> {idx}")
        backtest_instruments_str = generate_backtest_instruments(
            sdef.tickers, bot_def.kind, bot_name, backtest_name
        )
        write_to_file(backtest_instruments_str, f"{base_backtest_path}/sets/set_{idx}/instruments.py")

        logger.info(f"generate runner for set -> {idx}")
        backtest_runner_str = backtest_runner_template.format(
            bot_kind=bot_def.kind,
            bot_name=bot_name,
            backtest_name=backtest_name,
            set_idx=idx,
            analyzers_name=bot_def.backtest.analyzers,
            starting_balance=backtest_def.broker.starting_balance,
        )
        write_to_file(backtest_runner_str, f"{base_backtest_path}/sets/set_{idx}/runner.py")

    logger.info("generate backtest strategies")
    backtest_strategies_str = generate_backtest_strategies(bot_def)
    write_to_file(backtest_strategies_str, f"{base_backtest_path}/strategies.py")


def generate_backtest_runs(name):
    bot_def = conf.bots[name]
    for backtest_run_name in bot_def.backtest.runs:
        logger.info(f"current -> `{backtest_run_name}`")
        generate_backtest(backtest_run_name, name, bot_def)
