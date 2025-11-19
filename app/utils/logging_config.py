import logging
import os
from logging.handlers import RotatingFileHandler
import json

LOG_DIR = "logs"

# Create folder if missing
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# JSON formatter (optional)
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
            "path": record.pathname,
        }
        return json.dumps(log)

def setup_logging(app):

    # ------------------------------
    # 1. Rotating File Handler (INFO)
    # ------------------------------
    info_handler = RotatingFileHandler(
        f"{LOG_DIR}/app.log",
        maxBytes=10_000_000,   # 10 MB
        backupCount=5
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s [%(pathname)s:%(lineno)d]"
        )
    )

    # ------------------------------
    # 2. Error Handler (ERROR logs only)
    # ------------------------------
    error_handler = RotatingFileHandler(
        f"{LOG_DIR}/error.log",
        maxBytes=10_000_000,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s [%(pathname)s:%(lineno)d]"
        )
    )

    # ------------------------------
    # 3. Console Handler (for Docker/Gunicorn)
    # ------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    ))

    # ------------------------------
    # Attach handlers to Flask logger
    # ------------------------------
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(info_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)

    app.logger.info("Logging system initialized")
