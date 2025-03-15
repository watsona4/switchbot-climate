import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessage  # noqa: F401
from paho.mqtt.enums import CallbackAPIVersion

from . import LOG


class Client(mqtt.Client):

    def __init__(self, host: str, port: int):
        super().__init__(callback_api_version=CallbackAPIVersion.VERSION2)

        self._host = host
        self._port = port

        self.devices = []
        self.zones = []

        self.enable_logger(LOG)

        self.connect(self._host, self._port)

    def setup_subscriptions(self):

        for zone in self.zones:
            zone.setup_subscriptions()

        for device in self.devices:
            device.setup_subscriptions()

    def on_connect(self, *args, **kwargs):

        if (reason_code := args[3]).is_failure:
            LOG.error(f"Could not connect to broker: {reason_code.getName()}")
        else:
            LOG.info(f"Connected to {self._host}:{self._port}")
