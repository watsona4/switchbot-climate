import pytest
from datetime import timedelta
from switchbot_climate.util import c_to_f, f_to_c, format_td

def test_c_to_f():
    assert c_to_f(0) == 32.0
    assert c_to_f(100) == 212.0
    assert c_to_f(-40) == -40.0
    assert c_to_f(37) == 98.6
    assert c_to_f(None) is None
    assert c_to_f("25") == 77.0

def test_f_to_c():
    assert f_to_c(32) == 0.0
    assert f_to_c(212) == 100.0
    assert f_to_c(-40) == -40.0
    assert f_to_c(98.6) == 37.0
    assert f_to_c(None) is None
    assert f_to_c("77") == 25.0

def test_format_td():
    assert format_td(timedelta(days=1, hours=2, minutes=3, seconds=4)) == "1 day, 2 hours, 3 minutes, 4 seconds"
    assert format_td(timedelta(days=2, hours=0, minutes=0, seconds=0)) == "2 days, 0 microseconds"
    assert format_td(timedelta(hours=1, minutes=1, seconds=1)) == "1 hour, 1 minutes, 1 second"
    assert format_td(timedelta(minutes=1, seconds=1)) == "1 minutes, 1 second"
    assert format_td(timedelta(seconds=1)) == "1 second"
    assert format_td(timedelta(milliseconds=1)) == "1 millisecond"
    assert format_td(timedelta(microseconds=1)) == "1 microseconds"