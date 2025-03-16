from unittest.mock import MagicMock, patch

import pytest
import requests

from switchbot_climate.client import Client
from switchbot_climate.device import Device
from switchbot_climate.remote import FanMode, Mode, Remote


@pytest.fixture
def remote():
    return Remote(token="test_token", key="test_key")


@pytest.fixture
def device():
    return Device("test_device_name")


def test_format_send_state():
    state = "25,2,3,on"
    formatted_state = Remote.format_send_state(state)
    assert formatted_state == "25,2,3,on -> temp=77.0, mode=cool, fan=medium, power=on"


@patch("requests.get")
def test_get_device_info(mock_get, remote):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "body": {
            "infraredRemoteList": [{"deviceId": "test_device_id", "deviceName": "test_device"}]
        }
    }
    mock_get.return_value = mock_response

    device_info = remote.get_device_info()
    assert device_info == [{"deviceId": "test_device_id", "deviceName": "test_device"}]


@patch("requests.get")
def test_get_device_info_failure(mock_get, remote):
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.reason = "Not Found"
    mock_get.return_value = mock_response

    with pytest.raises(requests.RequestException):
        remote.get_device_info()


def test_get_headers(remote):
    headers = remote._get_headers()
    assert "Authorization" in headers
    assert "Content-Type" in headers
    assert "t" in headers
    assert "sign" in headers
    assert "nonce" in headers


@patch("requests.post")
def test_post(mock_post, remote, device):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_post.return_value = mock_response
    mock_client = MagicMock(spec=Client)
    device.client = mock_client

    result = remote.post(device, temp=25.0, mode=Mode.COOL, fan_mode=FanMode.MEDIUM)
    assert remote.sent_mode == Mode.COOL
    assert remote.sent_state == "25,2,3,on"
    assert result is True


@patch("requests.post")
def test_post_none(mock_post, remote, device):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_post.return_value = mock_response
    mock_client = MagicMock(spec=Client)
    device.client = mock_client

    result = remote.post(device, temp=25.0, mode=Mode.NONE, fan_mode=FanMode.NONE)
    assert remote.sent_mode == Mode.NONE
    assert remote.sent_state == "25,4,1,on"
    assert result is True

    result = remote.post(device, temp=20.6, mode=Mode.OFF, fan_mode=FanMode.NONE)
    assert remote.sent_mode == Mode.OFF
    assert remote.sent_state == "21,4,1,off"
    assert result is True


@patch("requests.post")
def test_post_failure(mock_post, remote, device):
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.reason = "Bad Request"
    mock_post.return_value = mock_response
    mock_client = MagicMock(spec=Client)
    device.client = mock_client

    result = remote.post(device, temp=25.0, mode=Mode.COOL, fan_mode=FanMode.MEDIUM)
    assert result is False


def test_post_no_send(remote, device):
    remote.sent_state = "25,2,3,on"
    result = remote.post(device, temp=25.0, mode=Mode.COOL, fan_mode=FanMode.MEDIUM)
    assert result is True


@patch("requests.post")
def test_post_publish_send_state(mock_post, remote, device):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_post.return_value = mock_response

    with patch.object(device, "publish_send_state") as mock_publish_send_state:
        result = remote.post(device, temp=25.0, mode=Mode.COOL, fan_mode=FanMode.MEDIUM)
        mock_publish_send_state.assert_called_once_with("25,2,3,on")
        assert result is True
