import logging
import sys

def configure_logging():
    logger = logging.getLogger("onering")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.handlers = [handler]
