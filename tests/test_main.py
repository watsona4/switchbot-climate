import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from switchbot_climate.__main__ import main


@pytest.fixture
def mock_config():
    return """\
mqtt_host: localhost
mqtt_port: 1883
temperature_tol: 4.5
humidity_tol: 15
token: test_token
key: test_key
climates:
  Living_Room:
    temperature: 22
    humidity: 50
    mode: cool
    fan_mode: auto
    preset_mode: none
    temp_device_id: 1234567890ab
    clamp: aaa/ddd
zones:
  Zone1:
    - Living_Room
"""


@pytest.fixture
def mock_config_two():
    return """\
mqtt_host: localhost
mqtt_port: 1883
token: test_token
key: test_key
climates:
  Living_Room:
    temperature: 22
    humidity: 50
    mode: cool
    fan_mode: auto
    preset_mode: none
    temp_device_id: 1234567890ab
    clamp: aaa/ddd
    primary: true
  Bedroom:
    temperature: 22
    humidity: 50
    mode: cool
    fan_mode: auto
    preset_mode: none
    temp_device_id: cdef01234567
    clamp: aaa/ddd
zones:
  Zone1:
    - Living_Room
    - Bedroom
"""


@pytest.fixture
def mock_config_two_primary():
    return """\
mqtt_host: localhost
mqtt_port: 1883
token: test_token
key: test_key
climates:
  Living_Room:
    temperature: 22
    humidity: 50
    mode: cool
    fan_mode: auto
    preset_mode: none
    temp_device_id: 1234567890ab
    clamp: aaa/ddd
    primary: true
  Bedroom:
    temperature: 22
    humidity: 50
    mode: cool
    fan_mode: auto
    preset_mode: none
    temp_device_id: cdef01234567
    clamp: aaa/ddd
    primary: true
zones:
  Zone1:
    - Living_Room
    - Bedroom
"""


@pytest.fixture
def mock_config_three():
    return """\
mqtt_host: localhost
mqtt_port: 1883
token: test_token
key: test_key
climates:
  Living_Room:
    temperature: 22
    humidity: 50
    mode: cool
    fan_mode: auto
    preset_mode: none
    temp_device_id: 1234567890ab
    clamp: aaa/ddd
    primary: true
  Bedroom:
    temperature: 22
    humidity: 50
    mode: cool
    fan_mode: auto
    preset_mode: none
    temp_device_id: cdef01234567
    clamp: aaa/ddd
  Bathroom:
    temperature: 22
    humidity: 50
    mode: cool
    fan_mode: auto
    preset_mode: none
    temp_device_id: 89abcdef0123
    clamp: jjj/kkk
    primary: true
zones:
  Zone1:
    - Living_Room
    - Bedroom
  Zone2:
    - Bathroom
"""


@pytest.fixture
def mock_device_info():
    return [
        {"deviceName": "Living Room", "deviceId": "device123"},
    ]


@pytest.fixture
def mock_device_info_two(mock_device_info):
    mock_device_info.append(
        {"deviceName": "Bedroom", "deviceId": "device456"},
    )
    return mock_device_info


@pytest.fixture
def mock_device_info_three(mock_device_info_two):
    mock_device_info_two.append({"deviceName": "Bathroom", "deviceId": "device789"})
    return mock_device_info_two


@patch.object(Path, "read_text")
@patch("switchbot_climate.__main__.Client")
@patch("switchbot_climate.__main__.Remote")
def test_main_one_device(mock_remote, mock_client, mock_path, mock_config, mock_device_info):
    mock_path.return_value = mock_config
    mock_remote_instance = mock_remote.return_value
    mock_remote_instance.get_device_info.return_value = mock_device_info
    mock_client_instance = mock_client.return_value

    with patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(config="config.yaml", verbose=True),
    ):
        main()

    mock_path.assert_called_once()
    mock_client.assert_called_once_with("localhost", 1883)
    mock_remote.assert_called_once_with("test_token", "test_key")
    mock_remote_instance.get_device_info.assert_called_once()
    mock_client_instance.setup_subscriptions.assert_called_once()
    mock_client_instance.loop_forever.assert_called_once()

    devices = mock_client.return_value.devices

    assert len(devices) == 1
    assert devices[0].name == "Living_Room"
    assert devices[0].TOLERANCE == 4.5
    assert devices[0].HUMIDITY_TOLERANCE == 15
    assert devices[0].target_temp == 22
    assert devices[0].target_humidity == 50
    assert devices[0].mode == "cool"
    assert devices[0].fan_mode == "auto"
    assert devices[0].preset_mode == "none"
    assert devices[0].temp_device_id == "1234567890ab"
    assert devices[0].clamp_id == "aaa"
    assert devices[0].current_id == "ddd"
    assert devices[0].device_id == "device123"
    assert devices[0].primary is True

    zones = mock_client.return_value.zones

    assert len(zones) == 1
    assert zones[0].name == "Zone1"
    assert len(zones[0].devices) == 1
    assert zones[0].devices[0].name == "Living_Room"
    assert zones[0].primary.name == "Living_Room"


@patch.object(Path, "read_text")
@patch("switchbot_climate.__main__.Client")
@patch("switchbot_climate.__main__.Remote")
def test_main_two_devices(
    mock_remote, mock_client, mock_path, mock_config_two, mock_device_info_two
):
    mock_path.return_value = mock_config_two
    mock_remote_instance = mock_remote.return_value
    mock_remote_instance.get_device_info.return_value = mock_device_info_two

    with patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(config="config.yaml", verbose=True),
    ):
        main()

    devices = mock_client.return_value.devices

    assert len(devices) == 2
    assert devices[1].name == "Bedroom"
    assert devices[1].target_temp == 22
    assert devices[1].target_humidity == 50
    assert devices[1].mode == "cool"
    assert devices[1].fan_mode == "auto"
    assert devices[1].preset_mode == "none"
    assert devices[1].temp_device_id == "cdef01234567"
    assert devices[1].clamp_id == "aaa"
    assert devices[1].current_id == "ddd"
    assert devices[1].device_id == "device456"
    assert devices[1].primary is False

    zones = mock_client.return_value.zones

    assert len(zones[0].devices) == 2
    assert zones[0].devices[1].name == "Bedroom"
    assert zones[0].primary.name == "Living_Room"


@patch.object(Path, "read_text")
@patch("switchbot_climate.__main__.Client")
@patch("switchbot_climate.__main__.Remote")
def test_main_primary_error(
    mock_remote, mock_client, mock_path, mock_config_two_primary, mock_device_info_two
):
    mock_path.return_value = mock_config_two_primary
    mock_remote_instance = mock_remote.return_value
    mock_remote_instance.get_device_info.return_value = mock_device_info_two

    with patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(config="config.yaml", verbose=True),
    ):
        with pytest.raises(RuntimeError):
            main()


@patch.object(Path, "read_text")
@patch("switchbot_climate.__main__.Client")
@patch("switchbot_climate.__main__.Remote")
def test_main_three_devices(
    mock_remote, mock_client, mock_path, mock_config_three, mock_device_info_three
):
    mock_path.return_value = mock_config_three
    mock_remote_instance = mock_remote.return_value
    mock_remote_instance.get_device_info.return_value = mock_device_info_three

    with patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(config="config.yaml", verbose=True),
    ):
        main()

    devices = mock_client.return_value.devices

    assert len(devices) == 3
    assert devices[2].name == "Bathroom"
    assert devices[2].target_temp == 22
    assert devices[2].target_humidity == 50
    assert devices[2].mode == "cool"
    assert devices[2].fan_mode == "auto"
    assert devices[2].preset_mode == "none"
    assert devices[2].temp_device_id == "89abcdef0123"
    assert devices[2].clamp_id == "jjj"
    assert devices[2].current_id == "kkk"
    assert devices[2].device_id == "device789"
    assert devices[2].primary is True

    zones = mock_client.return_value.zones

    assert len(zones) == 2
    assert zones[1].name == "Zone2"
    assert len(zones[1].devices) == 1
    assert zones[1].devices[0].name == "Bathroom"
    assert zones[1].primary.name == "Bathroom"


@patch.object(Path, "read_text")
@patch("switchbot_climate.__main__.Client")
@patch("switchbot_climate.__main__.Remote")
def test_main_interrupt(mock_remote, mock_client, mock_path, mock_config, mock_device_info):
    mock_path.return_value = mock_config
    mock_remote_instance = mock_remote.return_value
    mock_remote_instance.get_device_info.return_value = mock_device_info
    mock_client_instance = mock_client.return_value
    mock_client_instance.loop_forever = MagicMock(side_effect=KeyboardInterrupt)

    with patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(config="config.yaml", verbose=True),
    ):
        main()

    mock_client_instance.disconnect.assert_called_once()
