from phitech.logger import logger
from phitech import const

import os
import json


def generate_exploration_notebook(name):
    fname = f"{const.BASE_NOTEBOOKS_PATH}/exploration/{name}.ipynb"
    os.sytem(f"cp {const.BASE_NOTEBOOKS_PATH}/base.ipynb {fname}")
    logger.info("done.")
