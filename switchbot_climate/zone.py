from . import LOG


class Zone:

    def __init__(self, name: str):

        self.name = name

        self.devices = []
        self.primary = None
        self.client = None

        self.primary_initialized = False

    def get_auth(self, device_name: str, mode) -> bool:

        from .device import Mode

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
            LOG.info(f"Zone {self.name}:     granted :-)")
            self._sync(device_name, mode)
            return True

        LOG.info(f"Zone {self.name}:     DENIED :-(")
        return False

    def _sync(self, device_name: str, mode):

        from .device import Mode

        if not self.primary_initialized:
            return
        
        for device in self.devices:
            if device.name != device_name and device.mode != Mode.OFF:
                device.post_command(mode=mode if mode != Mode.OFF else device.mode)

    def setup_subscriptions(self):

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

    def other_mode(self):
        """If the primary doesn't need to set a mode because its temperature is in range,
        then set the mode of the other device in this zone.
        """
        for device in self.devices:
            if device != self.primary:
                return device.remote.sent_mode
        return None

    def is_primary(self, device):
        return self.primary == device
