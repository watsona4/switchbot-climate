from unittest.mock import MagicMock, patch

import pytest

from switchbot_climate.client import Client


@pytest.fixture
def client():
    with patch("switchbot_climate.client.LOG"):
        client = Client("localhost", 1883)
        yield client


def test_client_initialization(client):
    assert client._host == "localhost"
    assert client._port == 1883
    assert client.devices == []
    assert client.zones == []


def test_client_setup_subscriptions(client):
    mock_device = MagicMock()
    mock_zone = MagicMock()
    client.devices.append(mock_device)
    client.zones.append(mock_zone)

    client.setup_subscriptions()

    mock_device.setup_subscriptions.assert_called_once()
    mock_zone.setup_subscriptions.assert_called_once()


def test_client_on_connect_success(client):
    mock_reason_code = MagicMock()
    mock_reason_code.is_failure = False

    with patch("switchbot_climate.client.LOG") as mock_log:
        client.on_connect(None, None, None, mock_reason_code)
        mock_log.info.assert_called_with("Connected to localhost:1883")


def test_client_on_connect_failure(client):
    mock_reason_code = MagicMock()
    mock_reason_code.is_failure = True
    mock_reason_code.getName.return_value = "Connection Refused"

    with patch("switchbot_climate.client.LOG") as mock_log:
        client.on_connect(None, None, None, mock_reason_code)
        mock_log.error.assert_called_with("Could not connect to broker: Connection Refused")
