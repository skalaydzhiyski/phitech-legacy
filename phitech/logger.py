import sys
from loguru import logger


logger.remove()

logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <5}</level> | {message}",
    level="DEBUG",
    colorize=True,
)
logger = logger.bind(name='phitech-cli')
