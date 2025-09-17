import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(caller_file_name, console_level=logging.INFO, file_level=logging.DEBUG):
    # Define the log directory
    log_dir = os.path.join(os.path.dirname(__file__), "../logs")
    os.makedirs(log_dir, exist_ok=True)  # Ensure the folder exists
    log_file_path = os.path.join(log_dir, "app.log")

    # Create a logger, assuming that the caller file name is passed
    logger = logging.getLogger(os.path.splitext(os.path.basename(caller_file_name))[0])
    logger.setLevel(logging.DEBUG)  # Global level

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)

    # File Handler (Rotating)
    file_handler = RotatingFileHandler(log_file_path, maxBytes=5_000_000, backupCount=3)
    file_handler.setLevel(file_level)

    # Define Format
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt='%(levelname)-7s (%(asctime)s.%(msecs)03d) -> %(name)s: %(message)s', datefmt=date_format)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add Handlers (only if they haven't been added already)
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


