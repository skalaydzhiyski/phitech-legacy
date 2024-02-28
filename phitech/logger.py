import logging
from rich.pretty import get_console
from rich.style import Style


logger = logging.getLogger(__name__)
syslog = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s: %(message)s")
syslog.setFormatter(formatter)
logger.setLevel(logging.INFO)
logger.addHandler(syslog)

logger_pretty = get_console()
