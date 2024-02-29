from phitech import conf
from phitech.logger import logger


def strategy_filename_to_cls(name):
    return "".join([s.capitalize() for s in name.split("_")]) + "Strategy"


def write_to_file(string_content, filepath):
    logger.info(f"write file -> {filepath}")
    with open(filepath, "w") as f:
        f.write(string_content)
