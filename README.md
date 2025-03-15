# SwitchBot Climate

SwitchBot Climate is a Python package that integrates SwitchBot devices with MQTT to provide climate control functionalities. This package allows you to manage and control SwitchBot devices and zones, set target temperatures and humidity levels, and automate climate control based on predefined configurations.

## Features

- Control SwitchBot devices and zones via MQTT
- Set target temperatures and humidity levels
- Automate climate control based on configurations
- Monitor and log device states and actions

## Installation

To install the SwitchBot Climate package, clone the repository and install the required dependencies:

```bash
git clone https://github.com/yourusername/switchbot_climate.git
cd switchbot_climate
pip install -r requirements.txt
```
## Configuration

Create a configuration file in YAML format to define your devices and zones. Below is an example configuration file:

```yaml
mqtt_host: "your_mqtt_broker_host"
mqtt_port: 1883
token: "your_switchbot_api_token"
key: "your_switchbot_api_key"

climates:
  Living_Room:
    temperature: 22.0
    humidity: 50
    mode: "auto"
    fan_mode: "auto"
    preset_mode: "none"
    temp_device_id: "temp_device_id_1"
    clamp: "clamp_id_1"
    primary: true

zones:
  Home:
    - Living_Room
```

## Usage
To run the SwitchBot Climate application, use the following command:

```bash
python -m switchbot_climate -c path/to/your/config.yaml
```

## Example
Here is an example of how to use the SwitchBot Climate package in your Python code:

```python
import logging
from switchbot_climate import Client, Device, FanMode, Mode, PresetMode, Remote, Zone

# Set up logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("switchbot-climate")

# Define your configuration
config = {
    "mqtt_host": "your_mqtt_broker_host",
    "mqtt_port": 1883,
    "token": "your_switchbot_api_token",
    "key": "your_switchbot_api_key",
    "climates": {
        "Living_Room": {
            "temperature": 22.0,
            "humidity": 50,
            "mode": "auto",
            "fan_mode": "auto",
            "preset_mode": "none",
            "temp_device_id": "temp_device_id_1",
            "clamp": "clamp_id_1",
            "primary": True,
        }
    },
    "zones": {
        "Home": ["Living_Room"]
    }
}

# Initialize the client and remote
client = Client(config["mqtt_host"], config["mqtt_port"])
remote = Remote(config["token"], config["key"])

# Get device information
device_ids = {
    entry["deviceName"].replace(" ", "_"): entry["deviceId"]
    for entry in remote.get_device_info()
}

# Construct devices and zones
devices = []
for name, entry in config["climates"].items():
    device = Device(name)
    device.target_temp = entry["temperature"]
    device.target_humidity = entry["humidity"]
    device.mode = Mode(entry["mode"])
    device.fan_mode = FanMode(entry["fan_mode"])
    device.preset_mode = PresetMode(entry["preset_mode"])
    device.temp_device_id = entry["temp_device_id"]
    device.clamp = entry["clamp"]
    device.device_id = device_ids[name]
    device.client = client
    device.remote = remote
    if entry.get("primary"):
        device.primary = True
    devices.append(device)

zones = []
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
```

## License
This project is licensed under the MIT License. See the LICENSE file for details.
