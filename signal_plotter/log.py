import logging


def setup_logger():
    logger = logging.getLogger('simple_plotter')
    logger.setLevel(logging.INFO)
