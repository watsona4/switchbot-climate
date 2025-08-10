import argparse
import copy
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import List

from strictyaml import (
    Bool,
    Enum,
    Float,
    Int,
    Map,
    MapPattern,
    Optional,
    Regex,
    Seq,
    Str,
    Url,
    load,
)

from . import LOG, Client, Device, FanMode, Mode, PresetMode, Remote, Zone

# Schema for configuration file
SCHEMA = Map(
    {
        "mqtt_host": Url() | Str(),
        Optional("mqtt_port", 1883): Int(),
        Optional("mqtt_username", ""): Str(),
        Optional("mqtt_password", ""): Str(),
        Optional("topics"): Map(
            {
                Optional("device", default="switchbot_climate"): Str(),
                Optional("devices_root", default=""): Str(),
                Optional("switchbot", default="switchbot-mqtt"): Str(),
                Optional("zigbee2mqtt", default="zigbee2mqtt"): Str(),
            }
        ),
        Optional("health"): Map(
            {
                Optional("heartbeat_path", default="/tmp/switchbot_climate.heartbeat"): Str(),
                Optional("interval_seconds", default=15): Int(),
                Optional("grace_seconds", default=45): Int(),
            }
        ),
        Optional("temperature_tol", 3.0): Float(),
        Optional("humidity_tol", 5): Int(),
        "climates": MapPattern(
            Str(),
            Map(
                {
                    "temperature": Float(),
                    "humidity": Int(),
                    "mode": Enum(["off", "auto", "cool", "heat", "dry", "fan_only"]),
                    "fan_mode": Enum(["auto", "low", "medium", "high"]),
                    "preset_mode": Enum(["none", "away"]),
                    "temp_device_id": Regex(r"^[A-Fa-f0-9]{12}$"),
                    Optional("clamp_attr", default="current"): Str(),
                    Optional("primary", False): Bool(),
                }
            ),
            minimum_keys=1,
        ),
        "zones": MapPattern(
            Str(),
            Map(
                {
                    "clamp_topic": Str(),
                    "devices": Seq(Str()),
                }
            ),
        ),
        "token": Str(),
        "key": Str(),
    }
)


def _start_heartbeat(path: str, interval: int) -> threading.Event:
    stop_evt = threading.Event()

    def _loop() -> None:
        while not stop_evt.is_set():
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(str(time.time()))
            except Exception:
                LOG.exception("heartbeat write failed")
            stop_evt.wait(interval)

    t = threading.Thread(target=_loop, name="heartbeat", daemon=True)
    t.start()
    return stop_evt


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
    parser.add_argument(
        "--check-heartbeat",
        action="store_true",
        help="Exit 0 if heartbeat file is recent, else non-zero",
    )

    args = parser.parse_args()

    # Set up the logger based on args
    LOG.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # Read the config file
    config = load(Path(args.config).read_text(), SCHEMA).data

    health_cfg = config.get("health", {}) or {}
    hb_path = health_cfg.get("heartbeat_path", "/tmp/switchbot_climate.heartbeat")
    grace = int(health_cfg.get("grace_seconds", 45))

    if args.check_heartbeat:
        try:
            mtime = os.path.getmtime(hb_path)
        except FileNotFoundError:
            print("heartbeat missing")
            sys.exit(1)

            age = time.time() - mtime
            if age <= grace:
                print("ok")
                sys.exit(0)
            print(f"stale heartbeat: {age:.1f}s")
            sys.exit(1)

    mqtt_host = config["mqtt_host"]
    mqtt_port = config["mqtt_port"]
    mqtt_username = config["mqtt_username"]
    mqtt_password = config["mqtt_password"]
    token = config["token"]
    key = config["key"]

    if "temperature_tol" in config:
        Device.TOLERANCE = config["temperature_tol"]

    if "humidity_tol" in config:
        Device.HUMIDITY_TOLERANCE = config["humidity_tol"]

    client = Client(mqtt_host, mqtt_port, mqtt_username, mqtt_password, topics=config["topics"])

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
        device.mode = Mode(entry["mode"]) if "mode" in entry else Mode.NONE
        device.fan_mode = FanMode(entry["fan_mode"]) if "fan_mode" in entry else FanMode.NONE
        device.preset_mode = (
            PresetMode(entry["preset_mode"]) if "preset_mode" in entry else PresetMode.NONE
        )
        device.temp_device_id = entry["temp_device_id"]
        device.current_id = entry.get("clamp_attr", "current")

        device.device_id = device_ids[name]

        device.client = client
        device.remote = copy.deepcopy(remote)

        if "primary" in entry and entry["primary"]:
            device.primary = True

        devices.append(device)

    zones: List[Zone] = []
    for name, zcfg in config["zones"].items():
        zone = Zone(name)
        zone.client = client
        zone.clamp_topic = zcfg["clamp_topic"]

        for device in devices:
            if device.name in zcfg["devices"]:
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

    hb_stop_evt = _start_heartbeat(hb_path, health_cfg["interval_seconds"])

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        LOG.info("Shutting down...")
        try:
            hb_stop_evt.set()
        except Exception:
            pass
        for d in devices:
            try:
                client.publish(f"{d.name}/availability", "offline", qos=1, retain=True)
            except Exception:
                pass
        client.disconnect()


if __name__ == "__main__":
    main()  # pragma: no cover
