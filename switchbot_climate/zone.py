from typing import TYPE_CHECKING, List

from . import LOG
from .device import Mode

if TYPE_CHECKING:
    from .client import Client  # pragma: no cover
    from .device import Device  # pragma: no cover


class Zone:
    """
    Represents a zone in the SwitchBot climate control system.

    Attributes:
        name (str): The name of the zone.
        devices (List[Device]): A list of devices in the zone.
        primary (Device): The primary device in the zone.
        client (Client): The MQTT client for communication.
        primary_initialized (bool): Indicates if the primary device has been initialized.

    Methods:
        get_auth(device_name: str, mode: Mode) -> bool:

        _sync(device_name: str, mode: Mode):

        setup_subscriptions():

        on_clamp(*args, **kwargs):
            Handles clamp messages for the devices in the zone.

        other_mode() -> Mode:
            Determines the mode of the secondary device in the zone.

        is_primary(device) -> bool:
            Checks if the given device is the primary device.
    """

    def __init__(self, name: str):
        """
        Initializes a Zone instance.

        Args:
            name (str): The name of the zone.

        Attributes:
            name (str): The name of the zone.
            devices (List[Device]): A list of devices in the zone.
            primary (Device): The primary device in the zone.
            client (Client): The client associated with the zone.
            primary_initialized (bool): Flag indicating if the primary device is initialized.
        """

        self.name: str = name

        self.devices: List[Device] = []
        self.primary: Device = None
        self.client: Client = None

        self.primary_initialized: bool = False

    def get_auth(self, device_name: str, mode: Mode) -> bool:
        """
        Determines if a device is authorized to perform an action in a specific mode.

        This method checks if the primary device is initialized and if the requesting
        device matches the primary device. If the primary device is not initialized,
        it will initialize it. It then logs the authorization request and grants or
        denies access based on the current state of the primary device and its mode.

        Args:
            device_name (str): The name of the device requesting authorization.
            mode (Mode): The mode in which the device is requesting authorization.

        Returns:
            bool: True if the device is authorized, False otherwise.
        """

        if (
            self.primary_initialized is False
            and self.primary is not None
            and device_name == self.primary.name
        ):
            self.primary_initialized = True

        LOG.info(f"Zone {self.name}: {device_name} requesting auth for {mode=}...")
        if (
            self.primary is None
            or self.primary_initialized is False
            or device_name == self.primary.name
            or self.primary.mode == Mode.OFF
        ):
            LOG.info(f"Zone {self.name}:     \033[32mgranted :-)\033[0m")
            self._sync(device_name, mode)
            return True

        LOG.info(f"Zone {self.name}:     \033[31mDENIED :-(\033[0m")
        return False

    def _sync(self, device_name: str, mode: Mode):
        """
        Synchronizes the mode of devices in the zone.

        This method updates the mode of all devices in the zone except the one specified by `device_name`.
        Devices with mode `Mode.OFF` retain their current mode.

        Args:
            device_name (str): The name of the device to exclude from synchronization.
            mode (Mode): The mode to set for the other devices.

        Returns:
            None
        """

        if not self.primary_initialized:
            return

        for device in self.devices:
            if device.name != device_name and device.mode != Mode.OFF:
                device.post_command(mode=mode if mode != Mode.OFF else device.mode)

    def setup_subscriptions(self):
        """
        Sets up MQTT subscriptions for the devices in the zone.

        This method checks if there are any devices in the zone and ensures that all devices
        have the same clamp ID. It then subscribes to the MQTT topic corresponding to the clamp ID
        and adds a message callback for handling messages from that topic.

        Raises:
            RuntimeError: If there are no devices in the zone.
            RuntimeError: If there are multiple different clamp IDs in the zone.
        """

        if not self.devices:
            raise RuntimeError(f"Zone {self.name}: No devices in zone")

        clamp_id = None
        for device in self.devices:
            if clamp_id is not None and device.clamp_id != clamp_id:
                raise RuntimeError(f"Zone {self.name}: Multiple clamps in zone")
            clamp_id = device.clamp_id

        topic = f"zigbee2mqtt/{clamp_id}"

        self.client.subscribe(topic)
        self.client.message_callback_add(topic, self.on_clamp)

    def on_clamp(self, *args, **kwargs):
        for device in self.devices:
            device.on_clamp(*args, **kwargs)

    def other_mode(self) -> Mode:
        """Determines the mode of the secondary device in the zone.

        If the primary device does not need to set a mode because its temperature is within the desired range,
        this method sets the mode of the other device in the zone.

        Returns:
            Mode: The mode of the secondary device if found, otherwise None.
        """
        for device in self.devices:
            if device != self.primary:
                return device.remote.sent_mode
        return None

    def is_primary(self, device) -> bool:
        """Check if the given device is the primary device.

        Args:
            device: The device to check against the primary device.

        Returns:
            bool: True if the given device is the primary device, False otherwise.
        """
        return self.primary == device
