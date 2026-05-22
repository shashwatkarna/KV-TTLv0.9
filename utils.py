import time
import logging

def get_current_timestamp():
    """Returns the current timestamp in seconds."""
    return time.time()

def setup_logger(name="KV-MX9"):
    """Configures and returns a basic logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
