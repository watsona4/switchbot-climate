
from datetime import timedelta


def c_to_f(temp: float | str) -> float:
    """Convert Celsius to Fahrenheit.

    Args:
        temp (float | str): Temperature in Celsius. Can be a float or a string representation of a float.

    Returns:
        float: Temperature in Fahrenheit, rounded to one decimal place. Returns None if input is None.
    """
    return None if temp is None else round(float(temp) * 9 / 5 + 32, 1)


def f_to_c(temp: float | str) -> float:
    """Convert Fahrenheit to Celsius.

    Args:
        temp (float | str): Temperature in Fahrenheit. Can be a float or a string representation of a float.

    Returns:
        float: Temperature in Celsius, rounded to one decimal place. Returns None if input is None.
    """
    return None if temp is None else round((float(temp) - 32) * 5 / 9, 1)


def format_td(delta: timedelta) -> str:
    """
    Format a timedelta object into a human-readable string.

    Args:
        delta (timedelta): The timedelta object to format.

    Returns:
        str: A human-readable string representing the timedelta.
    """

    result = []
    if days := delta.days:
        result.append(f"{days} day{'s' if days > 1 else ''}")
    if hours := delta.seconds // 3600:
        result.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes := (delta.seconds % 3600) // 60:
        result.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds := delta.seconds % 60:
        result.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    elif milliseconds := delta.microseconds // 1000:
        result.append(f"{milliseconds} millisecond{'s' if milliseconds > 1 else ''}")
    elif microseconds := delta.microseconds:
        result.append(f"{microseconds} microsecond{'s' if microseconds > 1 else ''}")

    return ", ".join(result)
