from phitech import conf
from phitech.logger import logger_lib as logger


interval_to_timeframe_mapping = {
    "secs": "Seconds",
    "min": "Minutes",
    "mins": "Minutes",
    "hour": "Hours",
    "hours": "Hours",
    "day": "Days",
    "days": "Days",
    # Note: weeks in IB are 1W and months are 1M with no space...I don't even know
}


def parse_tradingview_ticker_string(ticker_str):
    instrument_str, alias = ticker_str.split("|")
    instrument_str = instrument_str.split("@")[1]
    symbol, exchange, n_bars, interval = instrument_str.split(".")
    return symbol, exchange, n_bars, interval, alias


def parse_ticker_string(ticker_str):
    instrument_str, range_str, alias = ticker_str.split("|")
    ticker, underlying_type, livetype, exchange, interval = instrument_str.split(".")
    if "/" not in range_str:
        range_str = conf.ranges[range_str]
    start_date, end_date = range_str.split("/")
    return (
        ticker,
        underlying_type,
        livetype,
        exchange,
        interval,
        alias,
        start_date,
        end_date,
    )


def filename_to_cls(name, suffix="Strategy"):
    return "".join([s.capitalize() for s in name.split("_")]) + suffix


def write_to_file(string_content, filepath):
    logger.info(f"write file -> {filepath}")
    with open(filepath, "w") as f:
        f.write(string_content)
