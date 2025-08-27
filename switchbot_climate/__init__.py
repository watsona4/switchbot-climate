"""
This module sets up logging for the SwitchBot Climate application and imports
the main classes used in the application.

Attributes:
    LOG (logging.Logger): The logger for the SwitchBot Climate application.
"""

import logging
import sys

LOG: logging.Logger = logging.getLogger(__name__)

_root = logging.getLogger()
if not _root.handlers:
    try:
        import colorlog

        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(
            colorlog.LevelFormatter(
                fmt={
                    "DEBUG": (
                        "[{asctime}] {log_color}({levelname})  {module}::{funcName}: {message}"
                    ),
                    "INFO": "[{asctime}] ({log_color}{levelname}{reset}) {blue}{message}",
                    "WARNING": "[{asctime}] {log_color}({levelname}) {message}",
                    "ERROR": "[{asctime}] {log_color}({levelname}) {message}",
                    "CRITICAL": "[{asctime}] {log_color}({levelname}) {message}",
                },
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red,bg_white",
                },
                style="{",
            )
        )
    except Exception:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
    _root.addHandler(h)

logging.getLogger("paho").setLevel(logging.WARNING)
logging.getLogger("paho.mqtt.client").setLevel(logging.WARNING)

from .client import Client  # noqa: F401,E402
from .device import Device, FanMode, Mode, PresetMode  # noqa: F401,E402
from .remote import Remote  # noqa: F401,E402
from .zone import Zone  # noqa: F401,E402
