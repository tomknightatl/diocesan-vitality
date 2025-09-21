import logging
import sys


def get_logger(name):
    """
    Configures and returns a logger with a standard format.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Console Handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # File Handler
        file_handler = logging.FileHandler("scraping.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
