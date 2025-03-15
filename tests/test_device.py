from datetime import datetime
from unittest.mock import MagicMock

import pytest

from switchbot_climate.device import Device, FanMode, Mode, PresetMode


@pytest.fixture
def device():
    client = MagicMock()
    device = Device(name="test_device")
    device.client = client
    device.remote = MagicMock()
    device.zone = MagicMock()
    return device


def test_initialization(device):
    assert device.name == "test_device"
    assert device._target_temp is None
    assert device._target_humidity is None
    assert device.mode is None
    assert device.fan_mode is None
    assert device.preset_mode is None
    assert device.temp_device_id is None
    assert device.clamp_id is None
    assert device.current_id is None
    assert device.action is None
    assert device.device_id is None
    assert device.remote is not None
    assert device.primary is False
    assert device.zone is not None
    assert device._temperature is None
    assert device._humidity is None
    assert device.client is not None
    assert device.last_sent_mode is None


def test_clamp_property(device):
    device.clamp = "clamp_id/current_id"
    assert device.clamp == "clamp_id"
    assert device.clamp_id == "clamp_id"
    assert device.current_id == "current_id"


def test_target_temp_property(device):
    device.target_temp = 25.678
    assert device.target_temp == 25.7


def test_target_humidity_property(device):
    device.target_humidity = 45.678
    assert device.target_humidity == 46


def test_temperature_property(device):
    device.temperature = 22.345
    assert device.temperature == 22.3


def test_humidity_property(device):
    device.humidity = 55.678
    assert device.humidity == 56


def test_setup_subscriptions(device):
    device.temp_device_id = "temp_device"
    device.setup_subscriptions()
    device.client.subscribe.assert_any_call("test_device/mode_cmd")
    device.client.subscribe.assert_any_call("switchbot/temp_device/status")


def test_subscribe(device):
    topic = "test_device/test_topic"
    callback = MagicMock()
    device.wrap_callback = MagicMock()

    device.subscribe(topic, callback)

    device.client.subscribe.assert_called_with(topic)
    device.wrap_callback.assert_called_with(topic, callback)


def test_wrap_callback(device):
    callback = MagicMock()
    topic = "test_device/test_topic"
    device.wrap_callback(topic, callback)

    message = MagicMock()
    message.payload.decode.return_value = "test_payload"
    device.last_message[0] = datetime.now()

    # Simulate the callback being called
    device.client.message_callback_add.call_args[0][1](None, None, message)

    callback.assert_called_with("test_payload")
    device.client.message_callback_add.assert_called_with(
        topic, device.client.message_callback_add.call_args[0][1]
    )


def test_on_mode(device):
    device.on_mode("cool")
    assert device.mode == Mode.COOL


def test_on_fan_mode(device):
    device.on_fan_mode("high")
    assert device.fan_mode == FanMode.HIGH


def test_on_target_temp(device):
    device.on_target_temp("23.5")
    assert device.target_temp == 23.5


def test_on_target_humidity(device):
    device.on_target_humidity("50")
    assert device.target_humidity == 50


def test_on_power(device):
    device.on_power("OFF")
    assert device.mode == Mode.OFF
    device.on_power("ON")
    assert device.mode == device.old_mode
    with pytest.raises(KeyError):
        device.on_power("INVALID")


def test_on_preset_mode(device):
    device.on_preset_mode("away")
    assert device.preset_mode == PresetMode.AWAY


def test_process_climate(device):
    device.post = MagicMock()
    device.compute_auto = MagicMock(return_value=(Mode.COOL, 25.0))
    device.compute_away = MagicMock(return_value=(Mode.COOL, Device.MAX_TEMP))

    device.mode = Mode.AUTO
    device.process_climate()
    device.post.assert_called_with(Mode.COOL, 25.0)

    device.post.reset_mock()
    device.preset_mode = PresetMode.AWAY
    device.process_climate()
    device.post.assert_called_with(Mode.COOL, Device.MAX_TEMP)
    device.preset_mode = PresetMode.NONE

    device.post.reset_mock()
    device.mode = Mode.OFF
    device.process_climate()
    device.post.assert_called_with(mode=Mode.OFF)

    device.post.reset_mock()
    device.mode = Mode.COOL
    device.process_climate()
    device.post.assert_called_with(mode=Mode.COOL)

    device.post.reset_mock()
    device.mode = Mode.HEAT
    device.process_climate()
    device.post.assert_called_with(mode=Mode.HEAT)

    device.post.reset_mock()
    device.mode = Mode.DRY
    device.process_climate()
    device.post.assert_called_with(mode=Mode.DRY)

    device.post.reset_mock()
    device.mode = Mode.FAN_ONLY
    device.process_climate()
    device.post.assert_called_with(mode=Mode.FAN_ONLY)


def test_on_switchbot(device):
    device.post = MagicMock()
    device.compute_auto = MagicMock(return_value=(Mode.COOL, 25.0))
    device.compute_away = MagicMock(return_value=(Mode.COOL, Device.MAX_TEMP))
    message = MagicMock()

    device.target_humidity = 50
    device.target_temp = 25.0

    message.payload.decode.return_value = '{"temperature": 22.5, "humidity": 55}'
    device.on_switchbot(None, None, message)
    assert device.temperature == 22.5
    assert device.humidity == 55

    device.preset_mode = PresetMode.AWAY
    device.on_switchbot(None, None, message)
    device.post.assert_called_with(Mode.COOL, Device.MAX_TEMP)
    device.preset_mode = PresetMode.NONE

    device.post.reset_mock()
    device.mode = Mode.COOL
    message.payload.decode.return_value = '{"temperature": 22.5, "humidity": 60}'
    device.on_switchbot(None, None, message)
    assert device.mode == Mode.DRY
    device.post.assert_called_with(mode=Mode.DRY)

    device.post.reset_mock()
    message.payload.decode.return_value = '{"temperature": 22.5, "humidity": 40}'
    device.on_switchbot(None, None, message)
    assert device.mode == Mode.COOL
    device.post.assert_called_with(mode=Mode.COOL, temp=25.0)

    device.post.reset_mock()
    device.mode = Mode.AUTO
    message.payload.decode.return_value = '{"temperature": 22.5, "humidity": 50}'
    device.on_switchbot(None, None, message)
    device.post.assert_called_with(Mode.COOL, 25.0)


def test_on_clamp(device):
    message = MagicMock()
    message.payload.decode.return_value = '{"current_id": 10.5}'

    device.current_id = "current_id"

    device.remote.sent_mode = Mode.OFF
    device.on_clamp(None, None, message)
    assert device.action == "off"

    device.remote.sent_mode = Mode.COOL
    device.on_clamp(None, None, message)
    assert device.action == "cooling"

    device.remote.sent_mode = Mode.HEAT
    device.on_clamp(None, None, message)
    assert device.action == "heating"

    device.remote.sent_mode = Mode.DRY
    device.on_clamp(None, None, message)
    assert device.action == "drying"

    device.remote.sent_mode = Mode.FAN_ONLY
    device.on_clamp(None, None, message)
    assert device.action == "fan"

    message.payload.decode.return_value = '{"current_id": 0}'
    device.on_clamp(None, None, message)
    assert device.action == "idle"


def test_compute_auto(device):
    device.target_temp = 22.0

    device.temperature = 24.0
    mode, temp = device.compute_auto()
    assert mode == Mode.COOL
    assert temp == 22.0

    device.temperature = 20.0
    mode, temp = device.compute_auto()
    assert mode == Mode.HEAT
    assert temp == 22.0

    device.temperature = 23.0
    device.zone.is_primary.return_value = True
    device.zone.other_mode.return_value = Mode.COOL
    mode, temp = device.compute_auto()
    assert mode == Mode.COOL
    assert temp == 22.0

    device.temperature = 23.0
    device.zone.is_primary.return_value = False
    device.last_sent_mode = Mode.HEAT
    mode, temp = device.compute_auto()
    assert mode == Mode.HEAT
    assert temp == 22.0


def test_compute_away(device):
    device.temperature = 31.0
    mode, temp = device.compute_away()
    assert mode == Mode.COOL
    assert temp == Device.MAX_TEMP

    device.temperature = 15.0
    mode, temp = device.compute_away()
    assert mode == Mode.HEAT
    assert temp == Device.MIN_TEMP

    device.temperature = 23.0
    device.target_temp = 22.0
    mode, temp, fan = device.compute_away()
    assert mode == Mode.FAN_ONLY
    assert temp == 22.0
    assert fan == FanMode.AUTO


def test_post(device):
    device.zone.get_auth = MagicMock(return_value=True)
    device.post_command = MagicMock()
    device.post(Mode.COOL, 25.0, FanMode.HIGH)
    device.post_command.assert_called_with(Mode.COOL, 25.0, FanMode.HIGH)


def test_post_command(device):
    device.remote.post = MagicMock(return_value=True)
    device.publish_states = MagicMock()

    device.post_command(Mode.COOL, 25.0, FanMode.HIGH)
    device.remote.post.assert_called_with(device, 25.0, Mode.COOL, FanMode.HIGH)
    device.publish_states.assert_called_once()
    assert device.last_sent_mode == Mode.COOL

    device.remote.post.reset_mock()
    device.publish_states.reset_mock()

    device.post_command(Mode.HEAT, 22.0, FanMode.LOW)
    device.remote.post.assert_called_with(device, 22.0, Mode.HEAT, FanMode.LOW)
    device.publish_states.assert_called_once()
    assert device.last_sent_mode == Mode.HEAT

    device.remote.post.reset_mock()
    device.publish_states.reset_mock()

    device.remote.post.return_value = False
    device.post_command(Mode.DRY, 20.0, FanMode.MEDIUM)
    device.remote.post.assert_called_with(device, 20.0, Mode.DRY, FanMode.MEDIUM)
    device.publish_states.assert_not_called()
    assert device.last_sent_mode == Mode.HEAT  # last_sent_mode should not change if post fails


def test_publish_measurements(device):
    device.temperature = 22.5
    device.humidity = 55
    device.publish_measurements()
    device.client.publish.assert_any_call("test_device/current_temperature", 22.5, retain=True)
    device.client.publish.assert_any_call("test_device/current_humidity", 55, retain=True)


def test_publish_states(device):
    device.mode = Mode.COOL
    device.preset_mode = PresetMode.AWAY
    device.fan_mode = FanMode.HIGH
    device.target_temp = 22.5
    device.target_humidity = 55
    device.publish_states()
    device.client.publish.assert_any_call("test_device/mode", Mode.COOL, retain=True)
    device.client.publish.assert_any_call("test_device/preset_mode", PresetMode.AWAY, retain=True)
    device.client.publish.assert_any_call("test_device/fan_mode", FanMode.HIGH, retain=True)
    device.client.publish.assert_any_call("test_device/target_temp", 22.5, retain=True)
    device.client.publish.assert_any_call("test_device/target_humidity", 55, retain=True)


def test_publish_action(device):
    device.action = "cooling"
    device.publish_action()
    device.client.publish.assert_called_with("test_device/action", "cooling", retain=True)


def test_publish_mode_cmd(device):
    device.mode = Mode.COOL
    device.publish_mode_cmd()
    device.client.publish.assert_called_with("test_device/mode_cmd", Mode.COOL, retain=True)
