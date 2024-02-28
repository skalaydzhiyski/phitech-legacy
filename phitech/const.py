import os


BASE_DEFINITIONS_PATH = f"{os.environ['PYTHONPATH']}/definitions"
BASE_STRATEGIES_PATH = f"{os.environ['PYTHONPATH']}/ip/strategies"
BASE_DATA_PATH = f"{os.environ['PYTHONPATH']}/data"
BASE_INDICATORS_PATH = f"{os.environ['PYTHONPATH']}/ip/indicators"
BASE_NOTEBOOKS_PATH = f"{os.environ['PYTHONPATH']}/notebooks"
BASE_BOTS_PATH = f"{os.environ['PYTHONPATH']}/bots"

TAB = "\t"

EMPTY_CODE_CELL = {
    "cell_type": "code",
    "execution_count": None,
    # "id": "9c7b5364-cb2f-4ebc-8c54-6c5f68cd2233",
    "metadata": {},
    "outputs": [],
    "source": [],
}

UNIVERSE_COLUMNS = [
    "name",
    "description",
    "exchange",
    "market_cap_basic",
]
