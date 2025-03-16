from typing import TYPE_CHECKING, List

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

    def __init__(self, host: str, port: int):
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

        self.enable_logger(LOG)

        self.connect(self._host, self._port)

    def setup_subscriptions(self):
        """
        Set up MQTT subscriptions for all devices and zones.
        """
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
