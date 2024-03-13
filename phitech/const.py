import os


BASE_DEFINITIONS_PATH = f"{os.environ['PYTHONPATH']}/definitions"
BASE_STRATEGIES_PATH = f"{os.environ['PYTHONPATH']}/ip/strategies"
BASE_DATA_PATH = f"{os.environ['PYTHONPATH']}/data"
BASE_INDICATORS_PATH = f"{os.environ['PYTHONPATH']}/ip/indicators"
BASE_ANALYZERS_PATH = f"{os.environ['PYTHONPATH']}/ip/analyzers"
BASE_OBSERVERS_PATH = f"{os.environ['PYTHONPATH']}/ip/observers"
BASE_SIZERS_PATH = f"{os.environ['PYTHONPATH']}/ip/sizers"
BASE_NOTEBOOKS_PATH = f"{os.environ['PYTHONPATH']}/notebooks"

BASE_BOTS_PATH = f"{os.environ['PYTHONPATH']}/bots"

TAB = "\t"

NOTEBOOK_BASE = {
 "cells": [
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.11.8"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}

UNIVERSE_COLUMNS = [
    "name",
    "description",
    "exchange",
    "market_cap_basic",
]
