"""Stores the common values and classes, and exposes the other modules."""

import logging

import colorlog

LOG: logging.Logger = logging.getLogger("switchbot-climate")

_handler = logging.StreamHandler()

_formatter = colorlog.LevelFormatter(
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

_handler.setFormatter(_formatter)

LOG.addHandler(_handler)
