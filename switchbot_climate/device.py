import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Callable, List, Tuple

from . import LOG
from .client import Client, MQTTClient, MQTTMessage
from .util import c_to_f, format_td


class Mode(StrEnum):
    """
    Enum representing the different modes of the device.
    """

    NONE = "none"
    OFF = "off"
    AUTO = "auto"
    COOL = "cool"
    HEAT = "heat"
    DRY = "dry"
    FAN_ONLY = "fan_only"


class FanMode(StrEnum):
    """
    Enum representing the different fan modes of the device.
    """

    NONE = "none"
    AUTO = "auto"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PowerMode(StrEnum):
    """
    Enum representing the power modes of the device.
    """

    ON = "ON"
    OFF = "OFF"


class PresetMode(StrEnum):
    """
    Enum representing the preset modes of the device.
    """

    NONE = "none"
    AWAY = "away"


class Device:
    """
    A class representing a device controlled by the SwitchBot API.

    Attributes:
        AWAY_MIN_TEMP (float): The lower threshold temperature during Away Mode.
        MIN_TEMP (float): The minimum temperature the device can be set to.
        MAX_TEMP (float): The maximum temperature the device can be set to.
        TOLERANCE (float): The temperature tolerance for the device.
        MIN_HUMIDITY (int): The minimum humidity the device can be set to.
        MAX_HUMIDITY (int): The maximum humidity the device can be set to.
        HUMIDITY_TOLERANCE (int): The humidity tolerance for the device.
        last_message (List[datetime]): A list containing the timestamp of the last message received.
    """

    AWAY_MIN_TEMP: float = 10.0
    MIN_TEMP: float = 16.0
    MAX_TEMP: float = 30.0
    TOLERANCE: float = 1.0

    MIN_HUMIDITY: int = 30
    MAX_HUMIDITY: int = 100
    HUMIDITY_TOLERANCE: int = 5

    last_message: List[datetime] = [datetime.now()]

    def __init__(self, name: str):
        """
        Initialize the Device class with the given name.

        Args:
            name (str): The name of the device.
        """
        self.name: str = name

        self._target_temp: float = 0.0
        self._target_humidity: int = 0

        self.mode: Mode = Mode.NONE
        self.fan_mode: FanMode = FanMode.NONE
        self.preset_mode: PresetMode = PresetMode.NONE
        self.temp_device_id: str = ""
        self.clamp_id: str = ""
        self.current_id: str = ""
        self.action: str = ""

        self.device_id: str = ""
        self.remote: Remote
        self.primary: bool = False
        self.zone: Zone

        self._temperature: float = 0.0
        self._humidity: int = 0

        self.client: Client

        self.old_mode: Mode = Mode.NONE
        self.old_target_temp: float = 0.0
        self.last_sent_mode: Mode = Mode.NONE
        self.last_action: str = ""

    @property
    def clamp(self) -> str:
        """
        Get the clamp ID.

        Returns:
            str: The clamp ID.
        """
        return self.clamp_id

    @clamp.setter
    def clamp(self, clamp: str):
        """
        Set the clamp ID.

        Args:
            clamp (str): The clamp ID.
        """
        self.clamp_id, self.current_id = clamp.split("/")

    @property
    def target_temp(self) -> float:
        """
        Get the target temperature.

        Returns:
            float: The target temperature.
        """
        return self._target_temp

    @target_temp.setter
    def target_temp(self, target_temp: float):
        """
        Set the target temperature.

        Args:
            target_temp (float): The target temperature.
        """
        self._target_temp = round(target_temp, 1)

    @property
    def target_humidity(self) -> int:
        """
        Get the target humidity.

        Returns:
            int: The target humidity.
        """
        return self._target_humidity

    @target_humidity.setter
    def target_humidity(self, target_humidity: float):
        """
        Set the target humidity.

        Args:
            target_humidity (float): The target humidity.
        """
        self._target_humidity = round(target_humidity)

    @property
    def temperature(self) -> float:
        """
        Get the current temperature.

        Returns:
            float: The current temperature.
        """
        return self._temperature

    @temperature.setter
    def temperature(self, temperature: float):
        """
        Set the current temperature.

        Args:
            temperature (float): The current temperature.
        """
        self._temperature = round(temperature, 1)

    @property
    def humidity(self) -> int:
        """
        Get the current humidity.

        Returns:
            int: The current humidity.
        """
        return self._humidity

    @humidity.setter
    def humidity(self, humidity: float):
        """
        Set the current humidity.

        Args:
            humidity (float): The current humidity.
        """
        self._humidity = round(humidity)

    def setup_subscriptions(self):
        """
        Set up MQTT subscriptions for the device.
        """
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
        """
        Subscribe to an MQTT topic.

        Args:
            topic (str): The MQTT topic to subscribe to.
            callback (Callable[[str], None]): The callback function to handle messages.
        """
        self.client.subscribe(topic)
        self.wrap_callback(topic, callback)

    def wrap_callback(self, topic: str, callback: Callable[[str], None]):
        """
        Wrap the callback function for an MQTT topic.

        Args:
            topic (str): The MQTT topic.
            callback (Callable[[str], None]): The callback function to handle messages.
        """

        def callback_wrapper(client: MQTTClient, userdata: Any, message: MQTTMessage):
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
        """
        Handle mode command messages.

        Args:
            payload (str): The payload of the mode command message.
        """
        if self.mode != Mode.OFF:
            self.old_mode = self.mode
            self.mode = Mode(payload)

    def on_fan_mode(self, payload: str):
        """
        Handle fan mode command messages.

        Args:
            payload (str): The payload of the fan mode command message.
        """
        self.fan_mode = FanMode(payload)

    def on_target_temp(self, payload: str):
        """
        Handle target temperature command messages.

        Args:
            payload (str): The payload of the target temperature command message.
        """
        self.old_target_temp = self.target_temp
        self.target_temp = float(payload)

    def on_target_humidity(self, payload: str):
        """
        Handle target humidity command messages.

        Args:
            payload (str): The payload of the target humidity command message.
        """
        self.target_humidity = int(payload)

    def on_power(self, payload: str):
        """
        Handle power command messages.

        Args:
            payload (str): The payload of the power command message.
        """
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
        """
        Handle preset mode command messages.

        Args:
            payload (str): The payload of the preset mode command message.
        """
        self.preset_mode = PresetMode(payload)

    def process_climate(self):
        """
        Process the climate control logic based on the current mode and conditions.
        """
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

    def on_switchbot(self, client: MQTTClient, userdata: Any, message: MQTTMessage):
        """
        Handle messages from the SwitchBot device.

        Args:
            client (Client): The MQTT client.
            userdata (Any): User data.
            message (MQTTMessage): The MQTT message.
        """
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

    def on_clamp(self, client: MQTTClient, userdata: Any, message: MQTTMessage):
        """
        Handle messages from the clamp device.

        Args:
            client (Client): The MQTT client.
            userdata (Any): User data.
            message (MQTTMessage): The MQTT message.
        """
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

        if self.action != self.last_action:
            self.last_action = self.action
            LOG.info(f"{self.name}: setting action to {self.action}")

        self.publish_action()

    def compute_auto(self) -> Tuple[Mode, float]:
        """
        Compute the mode and temperature for AUTO mode.

        Returns:
            Tuple[Mode, float]: The mode and temperature for AUTO mode.
        """
        bottom = round(self.target_temp - Device.TOLERANCE, 1)
        top = round(self.target_temp + Device.TOLERANCE, 1)

        str_bottom = c_to_f(bottom)
        str_top = c_to_f(top)
        str_temp = c_to_f(self.temperature)

        if self.temperature != 0.0:
            if self.temperature >= top:
                LOG.info(
                    f"{self.name}: temperature ({str_temp}) >= target_high"
                    f" ({str_top}), setting mode to COOL"
                )
                return Mode.COOL, self.target_temp
            if self.temperature < bottom:
                LOG.info(
                    f"{self.name}: temperature ({str_temp}) < target_low"
                    f" ({str_bottom}), setting mode to HEAT"
                )
                return Mode.HEAT, self.target_temp

        if self.zone.is_primary(self):
            mode = self.zone.other_mode()
            mode_str = f"getting mode from secondary device ({mode})"
        else:
            mode = self.last_sent_mode
            mode_str = f"not changing mode ({mode})"

        LOG.info(
            f"{self.name}: temperature ({str_temp}) in valid range"
            f" ({str_bottom}-{str_top}), {mode_str}"
        )

        return mode, self.target_temp

    def compute_away(self) -> Tuple[Mode, float, FanMode]:
        """
        Compute the mode, temperature, and fan mode for AWAY mode.

        Returns:
            Tuple[Mode, float, FanMode]: The mode, temperature, and fan mode for AWAY mode.
        """
        if self.temperature >= Device.MAX_TEMP:
            LOG.info(
                f"{self.name}: temperature ({c_to_f(self.temperature)}) >= MAX_TEMP"
                f" ({c_to_f(Device.MAX_TEMP)}), setting away mode to COOL"
            )
            return Mode.COOL, Device.MAX_TEMP, FanMode.NONE
        if self.temperature < Device.AWAY_MIN_TEMP:
            LOG.info(
                f"{self.name}: temperature ({c_to_f(self.temperature)}) < AWAY_MIN_TEMP"
                f" ({c_to_f(Device.AWAY_MIN_TEMP)}), setting away mode to HEAT"
            )
            return Mode.HEAT, Device.MIN_TEMP, FanMode.NONE
        LOG.info(
            f"{self.name}: temperature ({c_to_f(self.temperature)}) in valid range"
            f" ({c_to_f(Device.AWAY_MIN_TEMP)}-{c_to_f(Device.MAX_TEMP)}), setting away mode to"
            " FAN_ONLY"
        )
        return Mode.FAN_ONLY, self.target_temp, FanMode.AUTO

    def post(self, mode: Mode, temp: float = None, fan_mode: FanMode = FanMode.NONE):
        """
        Post a command to the device.

        Args:
            mode (Mode): The mode to set.
            temp (float, optional): The temperature to set. Defaults to None.
            fan_mode (FanMode, optional): The fan mode to set. Defaults to None.
        """
        if mode == self.last_sent_mode or self.zone.get_auth(self.name, mode):
            self.post_command(mode, temp, fan_mode)

    def post_command(self, mode: Mode, temp: float = None, fan_mode: FanMode = FanMode.NONE):
        """
        Post a command to the device.

        Args:
            mode (Mode): The mode to set.
            temp (float, optional): The temperature to set. Defaults to None.
            fan_mode (FanMode, optional): The fan mode to set. Defaults to None.
        """
        LOG.info(f"{self.name}: Posting {temp=}, {mode=}, {fan_mode=}")

        temp = temp or self.target_temp
        fan_mode = fan_mode or self.fan_mode

        if self.remote.post(self, temp, mode, fan_mode):
            self.last_sent_mode = mode
            self.publish_states()

    def publish_measurements(self):
        """
        Publish the current temperature and humidity measurements.
        """
        self.client.publish(f"{self.name}/current_temperature", self.temperature, retain=True)
        self.client.publish(f"{self.name}/current_humidity", self.humidity, retain=True)

    def publish_states(self):
        """
        Publish the current states of the device.
        """
        self.client.publish(f"{self.name}/mode", self.mode, retain=True)
        self.client.publish(f"{self.name}/preset_mode", self.preset_mode, retain=True)
        self.client.publish(f"{self.name}/fan_mode", self.fan_mode, retain=True)
        self.client.publish(f"{self.name}/target_humidity", self.target_humidity, retain=True)
        self.client.publish(f"{self.name}/action", self.action, retain=True)

        if self.preset_mode == PresetMode.AWAY:
            self.client.publish(f"{self.name}/target_temp_low", self.AWAY_MIN_TEMP, retain=True)
            self.client.publish(f"{self.name}/target_temp_high", self.MAX_TEMP, retain=True)
        else:
            if self.mode == Mode.AUTO:
                self.client.publish(
                    f"{self.name}/target_temp_low",
                    self.target_temp - Device.TOLERANCE,
                    retain=True,
                )
                self.client.publish(
                    f"{self.name}/target_temp_high",
                    self.target_temp + Device.TOLERANCE,
                    retain=True,
                )
            else:
                self.client.publish(f"{self.name}/target_temp", self.target_temp, retain=True)

    def publish_send_state(self, send_state: str):
        """
        Publish the send state of the device.

        Args:
            send_state (str): The send state to publish.
        """
        self.client.publish(
            f"{self.name}/attributes",
            json.dumps(
                {
                    "send_state": send_state,
                    "send_state_long": Remote.format_send_state(send_state),
                    "recv_mode": self.mode,
                    "recv_fan": self.fan_mode,
                    "recv_preset": self.preset_mode,
                    "target_temp": self.target_temp,
                    "target_humidity": self.target_humidity,
                    "curr_temp": self.temperature,
                    "curr_humidity": self.humidity,
                }
            ),
            retain=True,
        )

    def publish_action(self):
        """
        Publish the current action of the device.
        """
        self.client.publish(f"{self.name}/action", self.action, retain=True)

    def publish_mode_cmd(self):
        """
        Publish the mode command of the device.
        """
        self.client.publish(f"{self.name}/mode_cmd", self.mode, retain=True)


from .remote import Remote  # noqa: E402
from .zone import Zone  # noqa: E402
