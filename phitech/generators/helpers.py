from phitech import conf
from phitech.logger import logger


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


def parse_ticker_string(ticker_str):
    instrument_str, range_str, alias = ticker_str.split("|")
    ticker, underlying_type, livetype, exchange, interval = instrument_str.split(".")
    if '/' not in range_str:
        range_str = conf.ranges[range_str]
    start_date, end_date = range_str.split("/")
    return (ticker, underlying_type, livetype, exchange, interval, alias, start_date, end_date)


def parse_sets_string(sets_string, name=None):
    if isinstance(sets_string, int):
        return [sets_string]
    if sets_string.strip() == "all":
        n_sets = conf.instruments[name].sets
        return list(range(len(n_sets)))
    elif "-" in sets_string.strip():
        left, right = list(map(int, sets_string.split("-")))
        return list(range(left, right + 1))
    elif "," in sets_string.strip():
        return list(map(int, sets_string.strip().split(",")))


def filename_to_cls(name, suffix="Strategy"):
    return "".join([s.capitalize() for s in name.split("_")]) + suffix


def write_to_file(string_content, filepath):
    logger.info(f"write file -> {filepath}")
    with open(filepath, "w") as f:
        f.write(string_content)
