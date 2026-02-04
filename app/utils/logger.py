import logging
import os
import graypy
from app.core.config import LOG_FILE, LOG_LEVEL, LOG_DIR


class AppLogger:
    """
    A custom logger class for the application.
    This class follows the Singleton pattern to ensure only one instance exists.
    This class saves logs in a local file and can send logs to graylog server
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AppLogger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        """Initializes the logger with file and console handlers."""
        self.logger = logging.getLogger("root")
        self.logger.handlers.clear()  # Clear existing handlers

        # Set the log level
        self.logger.setLevel(LOG_LEVEL)

        # Define the log message format with extra fields
        format_str = (
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )

        # Create custom formatter that includes extra fields
        class ExtraFormatter(logging.Formatter):
            def format(self, record):
                # Get the base formatted message
                formatted = super().format(record)

                # Add extra fields if they exist
                extra_fields = []
                for key, value in record.__dict__.items():
                    if key not in [
                        "name",
                        "msg",
                        "args",
                        "levelname",
                        "levelno",
                        "pathname",
                        "filename",
                        "module",
                        "lineno",
                        "created",
                        "asctime",
                        "message",
                        "exc_info",
                        "exc_text",
                        "stack_info",
                        "taskName",
                        # "msecs",
                        "relativeCreated",
                        "thread",
                        "threadName",
                        "processName",
                        "process",
                        # "funcName",
                    ]:
                        extra_fields.append(f"{key}={value}")

                if extra_fields:
                    formatted += f" | Extra: {', '.join(extra_fields)}"

                return formatted

        self.formatter = ExtraFormatter(format_str)

        # Add default handlers (file and console)
        self._add_file_handler()
        self._add_console_handler()

    def _add_file_handler(self):
        """Adds a file handler to the logger."""
        # Ensure log directory exists
        os.makedirs(LOG_DIR, exist_ok=True)

        # Create full log file path
        log_file_path = os.path.join(LOG_DIR, LOG_FILE)

        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)

    def _add_console_handler(self):
        """Adds a console handler to the logger."""
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

    def add_graylog_handler(self, graylog_server: str, graylog_port: int):
        """
        Adds a Graylog handler to the logger.

        Args:
            graylog_server (str): The Graylog server address.
            graylog_port (int): The Graylog server port.
        """
        try:
            graylog_handler = graypy.GELFUDPHandler(graylog_server, graylog_port)
            graylog_handler.setFormatter(self.formatter)
            self.logger.addHandler(graylog_handler)
            self.logger.info("Graylog handler added successfully.")
        except ImportError:
            self.logger.error(
                "graypy is not installed. Please install it with 'pip install graypy'."
            )
        except Exception as e:
            self.logger.error(f"Failed to add Graylog handler: {str(e)}")

    def get_logger(self):
        """Returns the configured logger instance."""
        return self.logger


# Singleton instance of the logger
logger_instance = AppLogger().get_logger()
