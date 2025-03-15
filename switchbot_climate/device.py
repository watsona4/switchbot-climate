import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Callable, List, Tuple

from . import LOG
from .client import Client, MQTTMessage
from .util import c_to_f, format_td


class Mode(StrEnum):
    OFF = "off"
    AUTO = "auto"
    COOL = "cool"
    HEAT = "heat"
    DRY = "dry"
    FAN_ONLY = "fan_only"


class FanMode(StrEnum):
    AUTO = "auto"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PowerMode(StrEnum):
    ON = "ON"
    OFF = "OFF"


class PresetMode(StrEnum):
    NONE = "none"
    AWAY = "away"


class Device:

    MIN_TEMP: float = 16.0
    MAX_TEMP: float = 30.0
    TOLERANCE: float = round(2.0 * 5 / 9, 1)

    MIN_HUMIDITY: int = 30
    MAX_HUMIDITY: int = 100
    HUMIDITY_TOLERANCE: int = 5

    last_message: List[datetime] = [datetime.now()]

    def __init__(self, name: str):

        self.name: str = name

        self._target_temp: float = None
        self._target_humidity: int = None
        self.mode: Mode = None
        self.fan_mode: FanMode = None
        self.preset_mode: PresetMode = None
        self.temp_device_id: str = None
        self.clamp_id: str = None
        self.current_id: str = None
        self.action: str = None

        self.device_id: str = None
        self.remote: Remote = None
        self.primary: bool = False
        self.zone: Zone = None

        self._temperature: float = None
        self._humidity: int = None

        self.client: Client = None

        self.old_mode: Mode = None
        self.old_target_temp: float = None
        self.last_sent_mode: Mode = None

    @property
    def clamp(self) -> str:
        return self.clamp_id

    @clamp.setter
    def clamp(self, clamp: str):
        self.clamp_id, self.current_id = clamp.split("/")

    @property
    def target_temp(self) -> float:
        return self._target_temp

    @target_temp.setter
    def target_temp(self, target_temp: float):
        self._target_temp = round(target_temp, 1)

    @property
    def target_humidity(self) -> int:
        return self._target_humidity

    @target_humidity.setter
    def target_humidity(self, target_humidity: float):
        self._target_humidity = round(target_humidity)

    @property
    def temperature(self) -> float:
        return self._temperature

    @temperature.setter
    def temperature(self, temperature: float):
        self._temperature = round(temperature, 1)

    @property
    def humidity(self) -> int:
        return self._humidity

    @humidity.setter
    def humidity(self, humidity: float):
        self._humidity = round(humidity)

    def setup_subscriptions(self):

        self.subscribe(f"{self.name}/mode_cmd", self.on_mode)
        self.subscribe(f"{self.name}/fan_mode_cmd", self.on_fan_mode)
        self.subscribe(f"{self.name}/target_temp_cmd", self.on_target_temp)
        self.subscribe(f"{self.name}/target_humidity_cmd", self.on_target_humidity)
        self.subscribe(f"{self.name}/power_cmd", self.on_power)
        self.subscribe(f"{self.name}/preset_mode_cmd", self.on_preset_mode)
        self.client.subscribe(f"switchbot/{self.temp_device_id}/status")
        self.client.message_callback_add(
            f"switchbot/{self.temp_device_id}/status", self.on_switchbot
        )

    def subscribe(self, topic: str, callback: Callable[[str], None]):
        self.client.subscribe(topic)
        self.wrap_callback(topic, callback)

    def wrap_callback(self, topic: str, callback: Callable[[str], None]):

        def callback_wrapper(client: Client, userdata: Any, message: MQTTMessage):
            time_str = format_td(datetime.now() - self.last_message[0])
            self.last_message[0] = datetime.now()
            payload: str = message.payload.decode()
            LOG.info(
                f"\033[1;32m{self.name}: {time_str} later...received {payload} from"
                f" {message.topic}\033[0m"
            )
            callback(payload)
            self.process_climate()

        self.client.message_callback_add(topic, callback_wrapper)

    def on_mode(self, payload: str):
        if self.mode != Mode.OFF:
            self.old_mode = self.mode
            self.mode = Mode(payload)

    def on_fan_mode(self, payload: str):
        self.fan_mode = FanMode(payload)

    def on_target_temp(self, payload: str):
        self.old_target_temp = self.target_temp
        self.target_temp = float(payload)

    def on_target_humidity(self, payload: str):
        self.target_humidity = int(payload)

    def on_power(self, payload: str):
        if payload == PowerMode.OFF:
            self.old_mode = self.mode if self.mode != Mode.OFF else self.old_mode
            self.mode = Mode.OFF
            self.publish_mode_cmd()
        elif payload == PowerMode.ON:
            self.mode = self.old_mode
            self.publish_mode_cmd()
        else:
            raise KeyError(f"Invalid power mode requested: {self.name}: {payload}")

    def on_preset_mode(self, payload: str):
        self.preset_mode = PresetMode(payload)

    def process_climate(self):

        if self.preset_mode == PresetMode.AWAY and self.mode != Mode.OFF:
            LOG.info(f"{self.name}: In AWAY mode")
            self.post(*self.compute_away())

        else:
            match self.mode:
                case Mode.AUTO:
                    self.post(*self.compute_auto())
                case Mode.COOL:
                    self.post(mode=Mode.COOL)
                case Mode.HEAT:
                    self.post(mode=Mode.HEAT)
                case Mode.DRY:
                    self.post(mode=Mode.DRY)
                case Mode.FAN_ONLY:
                    self.post(mode=Mode.FAN_ONLY)
                case Mode.OFF:
                    self.post(mode=Mode.OFF)

    def on_switchbot(self, client: Client, userdata: Any, message: MQTTMessage):

        time_str = format_td(datetime.now() - self.last_message[0])
        self.last_message[0] = datetime.now()

        msg = json.loads(message.payload.decode())

        self.temperature = float(msg["temperature"])
        self.humidity = int(msg["humidity"])

        LOG.info(
            f"\033[1;32m{self.name}: {time_str} later...received temperature ="
            f" {c_to_f(self.temperature)}°F, humidity = {self.humidity}%\033[0m"
        )

        self.publish_measurements()

        if self.preset_mode == PresetMode.AWAY:
            LOG.info(f"{self.name}: In AWAY mode")
            self.post(*self.compute_away())

        elif self.humidity > self.target_humidity + Device.HUMIDITY_TOLERANCE:
            LOG.info(
                f"{self.name}: humidity ({self.humidity}) > target_high"
                f" ({self.target_humidity + Device.HUMIDITY_TOLERANCE}), going into DRY"
                " mode"
            )
            self.old_mode = self.mode
            self.old_target_temp = self.target_temp
            self.mode = Mode.DRY
            self.post(mode=Mode.DRY)

        elif (
            self.mode == Mode.DRY
            and self.humidity < self.target_humidity - Device.HUMIDITY_TOLERANCE
        ):
            LOG.info(
                f"{self.name}: humidity ({self.humidity}) < target_low"
                f" ({self.target_humidity - Device.HUMIDITY_TOLERANCE}), coming out of "
                " DRY mode"
            )
            if self.old_mode != Mode.OFF:
                self.mode = self.old_mode
                self.post(mode=self.old_mode, temp=self.old_target_temp)

        elif self.mode is None or self.mode == Mode.AUTO:
            LOG.info(f"{self.name}: In AUTO mode, calculating updated mode")
            self.post(*self.compute_auto())

    def on_clamp(self, client: Client, userdata: Any, message: MQTTMessage):

        msg = json.loads(message.payload.decode())

        current = float(msg[self.current_id])

        if self.remote.sent_mode == Mode.OFF:
            self.action = "off"
        elif current > 0:
            match self.remote.sent_mode:
                case Mode.COOL:
                    self.action = "cooling"
                case Mode.HEAT:
                    self.action = "heating"
                case Mode.DRY:
                    self.action = "drying"
                case Mode.FAN_ONLY:
                    self.action = "fan"
        else:
            self.action = "idle"

        self.publish_action()

    def compute_auto(self) -> Tuple[Mode, float]:

        bottom = round(self.target_temp - Device.TOLERANCE, 1)
        top = round(self.target_temp + Device.TOLERANCE, 1)

        if self.temperature is not None:

            if self.temperature >= top:
                LOG.info(
                    f"{self.name}: temperature ({c_to_f(self.temperature)}) >= target_high"
                    f" ({c_to_f(top)}), setting mode to COOL"
                )
                return Mode.COOL, self.target_temp
            if self.temperature < bottom:
                LOG.info(
                    f"{self.name}: temperature ({c_to_f(self.temperature)}) < target_low"
                    f" ({c_to_f(bottom)}), setting mode to HEAT"
                )
                return Mode.HEAT, self.target_temp

        if self.zone.is_primary(self):
            mode = self.zone.other_mode()
            mode_str = f"getting mode from secondary device ({mode})"
        else:
            mode = self.last_sent_mode
            mode_str = f"not changing mode ({mode})"

        LOG.info(
            f"{self.name}: temperature ({c_to_f(self.temperature)}) in valid range"
            f" ({c_to_f(bottom)}-{c_to_f(top)}), {mode_str}"
        )

        return mode, self.target_temp

    def compute_away(self) -> Tuple[Mode, float, FanMode | None]:

        if self.temperature >= Device.MAX_TEMP:
            LOG.info(
                f"{self.name}: temperature ({c_to_f(self.temperature)}) >= MAX_TEMP"
                f" ({c_to_f(Device.MAX_TEMP)}), setting away mode to COOL"
            )
            return Mode.COOL, Device.MAX_TEMP
        if self.temperature < Device.MIN_TEMP:
            LOG.info(
                f"{self.name}: temperature ({c_to_f(self.temperature)}) < MIN_TEMP"
                f" ({c_to_f(Device.MIN_TEMP)}), setting away mode to HEAT"
            )
            return Mode.HEAT, Device.MIN_TEMP
        LOG.info(
            f"{self.name}: temperature ({c_to_f(self.temperature)}) in valid range"
            f" ({c_to_f(Device.MIN_TEMP)}-{c_to_f(Device.MAX_TEMP)}), setting away mode to"
            " FAN_ONLY"
        )
        return Mode.FAN_ONLY, self.target_temp, FanMode.AUTO

    def post(self, mode: Mode, temp: float = None, fan_mode: FanMode = None):

        if mode == self.last_sent_mode or self.zone.get_auth(self.name, mode):
            self.post_command(mode, temp, fan_mode)

    def post_command(self, mode: Mode, temp: float = None, fan_mode: FanMode = None):

        LOG.info(f"{self.name}: Posting {temp=}, {mode=}, {fan_mode=}")

        temp = temp or self.target_temp
        fan_mode = fan_mode or self.fan_mode

        if self.remote.post(self, temp, mode, fan_mode):
            self.last_sent_mode = mode
            self.publish_states()

    def publish_measurements(self):
        self.client.publish(f"{self.name}/current_temperature", self.temperature, retain=True)
        self.client.publish(f"{self.name}/current_humidity", self.humidity, retain=True)

    def publish_states(self):
        self.client.publish(f"{self.name}/mode", self.mode, retain=True)
        self.client.publish(f"{self.name}/preset_mode", self.preset_mode, retain=True)
        self.client.publish(f"{self.name}/fan_mode", self.fan_mode, retain=True)
        self.client.publish(f"{self.name}/target_temp", self.target_temp, retain=True)
        self.client.publish(f"{self.name}/target_humidity", self.target_humidity, retain=True)
        self.client.publish(f"{self.name}/action", self.action, retain=True)

    def publish_send_state(self, send_state: str):

        self.client.publish(
            f"{self.name}/attributes",
            json.dumps({
                "send_state": send_state,
                "send_state_long": Remote.format_send_state(send_state),
                "recv_mode": self.mode,
                "recv_fan": self.fan_mode,
                "recv_preset": self.preset_mode,
                "target_temp": self.target_temp,
                "target_humidity": self.target_humidity,
                "curr_temp": self.temperature,
                "curr_humidity": self.humidity,
            }),
            retain=True,
        )

    def publish_action(self):
        self.client.publish(f"{self.name}/action", self.action, retain=True)

    def publish_mode_cmd(self):
        self.client.publish(f"{self.name}/mode_cmd", self.mode, retain=True)


from .remote import Remote  # noqa: E402
from .zone import Zone  # noqa: E402
