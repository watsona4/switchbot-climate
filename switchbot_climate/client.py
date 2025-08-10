from typing import TYPE_CHECKING, Any, List

from paho.mqtt.client import Client as MQTTClient
from paho.mqtt.client import MQTTMessage  # noqa: F401
from paho.mqtt.enums import CallbackAPIVersion

from . import LOG

if TYPE_CHECKING:
    from .device import Device  # pragma: no cover
    from .zone import Zone  # pragma: no cover


class Client(MQTTClient):
    """
    A class to represent an MQTT client for SwitchBot devices and zones.

    Attributes:
        _host (str): The MQTT broker host.
        _port (int): The MQTT broker port.
        devices (List[Device]): A list of devices managed by the client.
        zones (List[Zone]): A list of zones managed by the client.
    """

    def __init__(self, host: str, port: int, username: str, password: str, topics: dict[str, str]):
        """
        Initialize the Client class with the given host and port.

        Args:
            host (str): The MQTT broker host.
            port (int): The MQTT broker port.
        """
        super().__init__(callback_api_version=CallbackAPIVersion.VERSION2)

        self._host: str = host
        self._port: int = port

        self.devices: List[Device] = []
        self.zones: List[Zone] = []

        self.topics: dict[str, str] = topics

        self.enable_logger(LOG)

        self.username_pw_set(username, password)

        self.connect(self._host, self._port)

    def _is_under(self, base_key: str, topic: str) -> bool:
        base = self.topics.get(base_key, "")
        return bool(base) and (topic == base or topic.startswith(base + "/"))

    def _normalize_topic(self, topic: str) -> str:
        # pass through if already absolute under any known base
        for key in ("device", "devices_root", "switchbot", "zigbee2mqtt"):
            if self._is_under(key, topic):
                return topic
        # remap short upstream roots
        if topic.startswith("switchbot/"):
            return f"{self.topics['switchbot']}/{topic}"
        if topic.startswith("zigbee2mqtt/"):
            return f"{self.topics['zigbee2mqtt']}/{topic}"
        # device-local: "<DeviceName>/..."
        first = topic.split("/", 1)[0]
        if any(getattr(d, "name", None) == first for d in self.devices):
            return f"{self.topics['devices_root']}/{topic}"
        # otherwise leave as-is (covers app health etc.)
        return topic

    def publish(self, topic, payload=None, qos: int = 0, retain: bool = False, properties=None):
        topic = self._normalize_topic(topic)
        return super().publish(topic, payload, qos=qos, retain=retain, properties=properties)

    def subscribe(self, topic: str, qos: int = 0, options=None, properties=None):
        topic = self._normalize_topic(topic)
        return super().subscribe(topic, qos=qos, options=options, properties=properties)

    def message_callback_add(self, sub: str, callback):
        sub = self._normalize_topic(sub)
        return super().message_callback_add(sub, callback)

    def setup_subscriptions(self):
        """
        Set up MQTT subscriptions for all devices and zones.
        """
        self.subscribe("switchbot_climate/healthcheck/status")
        self.message_callback_add("switchbot_climate/healthcheck/status", self.on_healthcheck)

        for zone in self.zones:
            zone.setup_subscriptions()

        for device in self.devices:
            device.setup_subscriptions()

    def on_connect(self, *args, **kwargs):  # type: ignore[override]
        """
        Handle the event when the client connects to the MQTT broker.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        if (reason_code := args[3]).is_failure:
            LOG.error(f"Could not connect to broker: {reason_code.getName()}")
        else:
            LOG.info(f"Connected to {self._host}:{self._port}")

    def on_healthcheck(self, client: MQTTClient, userdata: Any, message: MQTTMessage):
        """
        Handle the health check message from the MQTT broker.

        If the received message payload is "CHECK", the method responds by
        publishing "OK" to the "switchbot_climate/healthcheck/status" topic.

        Args:
            client (MQTTClient): The MQTT client instance.
            userdata (Any): User-defined data of any type passed to the callback.
            message (MQTTMessage): The MQTT message containing the payload.

        """
        if message.payload.decode() == "CHECK":
            self.publish("switchbot_climate/healthcheck/status", "OK")
