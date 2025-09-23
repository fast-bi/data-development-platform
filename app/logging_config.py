import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def get_log_level(level_name):
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return levels.get(level_name.upper(), logging.INFO)

class StreamToLogger(object):
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

def configure_logging(app):
    # Get log level from environment variable, default to INFO
    log_level = get_log_level(os.environ.get('LOG_LEVEL', 'INFO'))

    # Ensure the logs directory exists
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, 'app.log')
    
    print(f"Log file path: {log_file}")  # Debug print

    # Remove all existing handlers from the root logger and app logger
    for logger in [logging.getLogger(), app.logger]:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    # Configure the RotatingFileHandler
    try:
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=10485760,  # 10MB
            backupCount=10,
            delay=False  # Changed to False to create the file immediately
        )
    except Exception as e:
        print(f"Error creating RotatingFileHandler: {e}")  # Debug print
        return app

    # Set the logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Set the logging level
    file_handler.setLevel(log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)

    # Configure app logger
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)

    # Redirect stdout and stderr to the logger
    sys.stdout = StreamToLogger(app.logger, logging.INFO)
    sys.stderr = StreamToLogger(app.logger, logging.ERROR)

    # Don't propagate logs to parent loggers
    app.logger.propagate = False

    # Test log messages
    app.logger.debug("This is a debug message")
    app.logger.info("This is an info message")
    app.logger.warning("This is a warning message")
    app.logger.error("This is an error message")

    print(f"Logging configured with level: {logging.getLevelName(log_level)}")  # Debug print

    return app