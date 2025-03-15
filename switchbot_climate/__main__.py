import argparse
import copy
import logging
from typing import List

import yaml
from yaml import CLoader as Loader

from . import LOG, Client, Device, FanMode, Mode, PresetMode, Remote, Zone


def main():
    """
    Main function to set up and run the SwitchBot Climate application.
    """
    # Parse the command line arguments
    parser = argparse.ArgumentParser(
        prog="switchbot-climate", description="Adds a climate entity to SwitchBot-MQTT"
    )

    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "-c",
        "--config",
        help="Initializes the configuration from the indicated file",
        required=True,
    )

    args = parser.parse_args()

    # Set up the logger based on args
    LOG.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # Read the config file
    with open(args.config) as config_file:
        config = yaml.load(config_file, Loader=Loader)

    mqtt_host = config["mqtt_host"]
    mqtt_port = config["mqtt_port"] if "mqtt_port" in config else 1883
    token = config["token"]
    key = config["key"]

    client = Client(mqtt_host, mqtt_port)

    remote = Remote(token, key)
    device_ids = {
        entry["deviceName"].replace(" ", "_"): entry["deviceId"]
        for entry in remote.get_device_info()
    }

    # Construct the Device, Zone, and Remote objects based on the config
    devices: List[Device] = []
    for name, entry in config["climates"].items():
        device = Device(name)

        device.target_temp = entry["temperature"] if "temperature" in entry else None
        device.target_humidity = entry["humidity"] if "humidity" in entry else None
        device.mode = Mode(entry["mode"]) if "mode" in entry else None
        device.fan_mode = FanMode(entry["fan_mode"]) if "fan_mode" in entry else None
        device.preset_mode = PresetMode(entry["preset_mode"]) if "preset_mode" in entry else None
        device.temp_device_id = entry["temp_device_id"]
        device.clamp = entry["clamp"]

        device.device_id = device_ids[name]

        device.client = client
        device.remote = copy.deepcopy(remote)

        if "primary" in entry and entry["primary"]:
            device.primary = True

        devices.append(device)

    zones: List[Zone] = []
    for name, entries in config["zones"].items():
        zone = Zone(name)
        zone.client = client

        for device in devices:
            if device.name in entries:
                zone.devices.append(device)
                device.zone = zone

        if len(zone.devices) == 1:
            zone.primary = zone.devices[0]
            zone.primary.primary = True
        else:
            for device in zone.devices:
                if device.primary:
                    if zone.primary is None:
                        zone.primary = device
                    else:
                        raise RuntimeError("Only one device may be designated as primary")

        zones.append(zone)

    # Start the event loop
    client.devices = devices
    client.zones = zones
    client.setup_subscriptions()

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        LOG.info("Shutting down...")
        client.disconnect()


if __name__ == "__main__":
    main()  # pragma: no cover
