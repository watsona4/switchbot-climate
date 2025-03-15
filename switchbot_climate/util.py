"""Stores utliity functions."""

from datetime import timedelta


def c_to_f(temp: float | str) -> float:
    """Converts Celsius to Fahrenheit"""
    return None if temp is None else round(float(temp) * 9 / 5 + 32, 1)


def f_to_c(temp: float | str) -> float:
    """Converts Fahrenheit to Celsius"""
    return None if temp is None else round((float(temp) - 32) * 5 / 9, 1)


def format_td(delta: timedelta) -> str:
    """Formats a timedelta object as a human readable string"""

    result = ""
    if days := delta.days:
        result += f"{days} day{'s' if days > 1 else ''}, "
    if hours := delta.seconds // 3600:
        result += f"{hours} hour{'s' if hours > 1 else ''}, "
    if minutes := (delta.seconds % 3600) // 60:
        result += f"{minutes} minutes{'s' if minutes > 1 else ''}, "
    if seconds := delta.seconds % 60:
        result += f"{seconds} second{'s' if seconds > 1 else ''}"
    elif milliseconds := delta.microseconds // 1000:
        result += f"{milliseconds} millisecond{'s' if milliseconds > 1 else ''}"
    else:
        result += f"{delta.microseconds} microseconds"

    return result
