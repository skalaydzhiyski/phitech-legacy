import logging

bold = "\033[1m"
green = "\033[92m"
yellow = "\033[93m"
red = "\033[91m"
white = "\033[97m"
light_blue = "\033[94m"
blue = "\033[94m"
cyan = "\033[96m"
magenta = "\033[95m"
black = "\033[90m"
gray = "\033[90m"
light_gray = "\033[37m"
reset = "\033[0m"


class MyFormatter(logging.Formatter):
    err_fmt = "ERROR: %(msg)s"
    dbg_fmt = "DBG: %(module)s: %(lineno)d: %(msg)s"
    info_fmt = "%(msg)s"

    def __init__(self, fmt=""):
        logging.Formatter.__init__(self, fmt)

    def format(self, record):
        format_orig = self._style._fmt

        if record.levelname == "DEBUG":
            self._style._fmt = (
                f"{light_gray}%(asctime)s {reset}| {bold}{gray}%(levelname)-5s {reset}|  %(message)s"
            )

        elif record.levelname == "INFO":
            self._style._fmt = (
                f"{light_gray}%(asctime)s {reset}| {bold}{white}%(levelname)-5s {reset}| %(message)s"
            )

        elif record.levelname == "ERROR":
            self._style._fmt = (
                f"{light_gray}%(asctime)s {reset}| {bold}{red}%(levelname)-5s {reset}| %(message)s"
            )

        res = logging.Formatter.format(self, record)
        self._style._fmt = format_orig

        return res


handler = logging.StreamHandler()
formatter = MyFormatter()
handler.setFormatter(formatter)

logger_lib = logging.getLogger("phitech-lib")
logger_lib.addHandler(handler)
logger_lib.setLevel(logging.DEBUG)
