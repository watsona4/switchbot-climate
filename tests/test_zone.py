from unittest.mock import MagicMock

import pytest

from switchbot_climate.client import Client, MQTTMessage
from switchbot_climate.device import Device, Mode
from switchbot_climate.remote import Remote
from switchbot_climate.zone import Zone


@pytest.fixture
def mock_remote1():
    remote = MagicMock(spec=Remote)
    remote.sent_mode = Mode.OFF
    return remote


@pytest.fixture
def mock_remote2():
    remote = MagicMock(spec=Remote)
    remote.sent_mode = Mode.OFF
    return remote


@pytest.fixture
def mock_device1(mock_remote1):
    device = MagicMock(spec=Device)
    device.name = "Device1"
    device.mode = Mode.OFF
    device.clamp_id = "clamp1"
    device.remote = mock_remote1
    return device


@pytest.fixture
def mock_device2(mock_remote2):
    device = MagicMock(spec=Device)
    device.name = "Device2"
    device.mode = Mode.OFF
    device.clamp_id = "clamp2"
    device.remote = mock_remote2
    return device


@pytest.fixture
def mock_client():
    return MagicMock(spec=Client)


@pytest.fixture
def mock_zone1(mock_device1, mock_client):
    zone = Zone(name="Zone1")
    zone.devices.append(mock_device1)
    zone.primary = mock_device1
    zone.client = mock_client
    return zone


@pytest.fixture
def mock_zone2(mock_device1, mock_device2, mock_client):
    zone = Zone(name="Zone2")
    zone.devices.append(mock_device1)
    zone.devices.append(mock_device2)
    zone.primary = mock_device1
    zone.client = mock_client
    return zone


def test_get_auth_granted_one_device(mock_zone1):
    mock_zone1.primary_initialized = False
    assert mock_zone1.get_auth("Device1", Mode.COOL) is True


def test_get_auth_granted_two_devices(mock_zone2):
    mock_zone2.primary_initialized = False
    assert mock_zone2.get_auth("Device1", Mode.COOL) is True
    assert mock_zone2.get_auth("Device2", Mode.COOL) is True


def test_get_auth_denied_one_device(mock_zone1, mock_device1):
    mock_device1.name = "Device1"
    mock_zone1.primary_initialized = True
    mock_zone1.primary.mode = Mode.HEAT
    assert mock_zone1.get_auth("Device2", Mode.COOL) is False


def test_get_auth_denied_two_devices(mock_zone2):
    mock_zone2.primary_initialized = True
    mock_zone2.primary.mode = Mode.HEAT
    assert mock_zone2.get_auth("Device2", Mode.COOL) is False


def test_sync_one_device(mock_zone1, mock_device1):
    mock_zone1.primary_initialized = True
    mock_device1.mode = Mode.HEAT
    mock_zone1._sync("Device1", Mode.COOL)
    mock_device1.post_command.assert_not_called()


def test_sync_two_devices(mock_zone2, mock_device1, mock_device2):
    mock_zone2.primary_initialized = True
    mock_device1.mode = Mode.HEAT
    mock_device2.mode = Mode.COOL
    mock_zone2._sync("Device1", Mode.HEAT)
    mock_device2.post_command.assert_called_once_with(Mode.HEAT)


def test_sync_with_off_mode_one_device(mock_zone1, mock_device1):
    mock_zone1.primary_initialized = True
    mock_device1.mode = Mode.COOL
    mock_zone1._sync("Device1", Mode.OFF)
    mock_device1.post_command.assert_not_called()


def test_sync_with_off_mode_two_devices(mock_zone2, mock_device1, mock_device2):
    mock_zone2.primary_initialized = True
    mock_device1.mode = Mode.COOL
    mock_device2.mode = Mode.OFF
    mock_zone2._sync("Device1", Mode.OFF)
    mock_device2.post_command.assert_not_called()


def test_setup_subscriptions_no_devices(mock_zone1):
    mock_zone1.devices = []
    with pytest.raises(RuntimeError, match="Zone Zone1: No devices in zone"):
        mock_zone1.setup_subscriptions()


def test_sync_primary_uninitialized(mock_zone2, mock_device1, mock_device2):
    mock_zone2.primary_initialized = False
    mock_zone2._sync("Device1", Mode.HEAT)
    mock_device1.post_command.assert_not_called()
    mock_device2.post_command.assert_not_called()


def test_get_auth_primary_uninitialized(mock_zone2):
    mock_zone2.primary_initialized = False
    mock_zone2.primary = None
    assert mock_zone2.get_auth("Device1", Mode.COOL) is True


def test_get_auth_primary_initialized(mock_zone2):
    mock_zone2.primary_initialized = True
    mock_zone2.primary.mode = Mode.OFF
    assert mock_zone2.get_auth("Device1", Mode.COOL) is True


def test_get_auth_primary_mode_off(mock_zone2):
    mock_zone2.primary_initialized = True
    mock_zone2.primary.mode = Mode.OFF
    assert mock_zone2.get_auth("Device2", Mode.COOL) is True


def test_get_auth_primary_mode_on(mock_zone2):
    mock_zone2.primary_initialized = True
    mock_zone2.primary.mode = Mode.HEAT
    assert mock_zone2.get_auth("Device2", Mode.COOL) is False


def test_sync_devices_with_different_modes(mock_zone2, mock_device1, mock_device2):
    mock_zone2.primary_initialized = True
    mock_device1.mode = Mode.COOL
    mock_device2.mode = Mode.HEAT
    mock_zone2._sync("Device1", Mode.OFF)
    mock_device2.post_command.assert_called_once_with(Mode.HEAT)


def test_setup_subscriptions_multiple_clamps(mock_zone2, mock_device2):
    mock_device2.clamp_id = "clamp2"
    with pytest.raises(RuntimeError, match="Zone Zone2: Multiple clamps in zone"):
        mock_zone2.setup_subscriptions()


def test_setup_subscriptions_success(mock_zone1, mock_client):
    mock_zone1.setup_subscriptions()
    mock_client.subscribe.assert_called_once_with("zigbee2mqtt/clamp1")
    mock_client.message_callback_add.assert_called_once_with(
        "zigbee2mqtt/clamp1", mock_zone1.on_clamp
    )


def test_setup_subscriptions_two_devices(mock_zone2, mock_device2, mock_client):
    mock_device2.clamp_id = "clamp1"
    mock_zone2.setup_subscriptions()
    mock_client.subscribe.assert_called_once_with("zigbee2mqtt/clamp1")
    mock_client.message_callback_add.assert_called_once_with(
        "zigbee2mqtt/clamp1", mock_zone2.on_clamp
    )


def test_other_mode_one_device(mock_zone1, mock_device1):
    mock_device1.remote.sent_mode = Mode.HEAT
    assert mock_zone1.other_mode() == Mode.NONE


def test_other_mode_two_devices(mock_zone2, mock_device2):
    mock_device2.remote.sent_mode = Mode.COOL
    assert mock_zone2.other_mode() == Mode.COOL


def test_on_clamp_one_device(mock_zone1, mock_device1):
    mock_message = MagicMock(spec=MQTTMessage)
    mock_zone1.on_clamp(mock_zone1.client, None, mock_message)
    mock_device1.on_clamp.assert_called_once_with(mock_zone1.client, None, mock_message)


def test_on_clamp_two_devices(mock_zone2, mock_device1, mock_device2):
    mock_message = MagicMock(spec=MQTTMessage)
    mock_zone2.on_clamp(mock_zone2.client, None, mock_message)
    mock_device1.on_clamp.assert_called_once_with(mock_zone2.client, None, mock_message)
    mock_device2.on_clamp.assert_called_once_with(mock_zone2.client, None, mock_message)


def test_is_primary_one_device(mock_zone1, mock_device1):
    assert mock_zone1.is_primary(mock_device1) is True


def test_is_primary_two_devices(mock_zone2, mock_device1, mock_device2):
    assert mock_zone2.is_primary(mock_device1) is True
    assert mock_zone2.is_primary(mock_device2) is False
