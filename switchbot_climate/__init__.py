"""
This module sets up logging for the SwitchBot Climate application and imports
the main classes used in the application.

Attributes:
    LOG (logging.Logger): The logger for the SwitchBot Climate application.
"""

import logging

import colorlog

LOG: logging.Logger = logging.getLogger(__name__)

__handler = logging.StreamHandler()

__formatter = colorlog.LevelFormatter(
    fmt={
        "DEBUG": "[{asctime}] {log_color}({levelname})  {module}::{funcName}: {message}",
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

__handler.setFormatter(__formatter)  # type: ignore[arg-type]

LOG.addHandler(__handler)

from .client import Client  # noqa: F401,E402
from .device import Device, FanMode, Mode, PresetMode  # noqa: F401,E402
from .remote import Remote  # noqa: F401,E402
from .zone import Zone  # noqa: F401,E402
