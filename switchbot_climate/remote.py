import base64
import hashlib
import hmac
import time
import uuid
from typing import Dict, List

import requests

from . import LOG
from .device import Device, FanMode, Mode
from .util import c_to_f


class Remote:
    """
    A class to interact with the SwitchBot API for controlling remote devices.

    Attributes:
        endpoint (str): The API endpoint for SwitchBot.
        modes (Dict): A dictionary mapping Mode enums to their corresponding API values.
        fan_modes (Dict): A dictionary mapping FanMode enums to their corresponding API values.
    """

    endpoint: str = "https://api.switch-bot.com/v1.1"

    modes: Dict = {
        Mode.NONE: 4,
        Mode.OFF: 0,
        Mode.AUTO: 1,
        Mode.COOL: 2,
        Mode.DRY: 3,
        Mode.FAN_ONLY: 4,
        Mode.HEAT: 5,
    }

    fan_modes: Dict = {
        FanMode.NONE: 1,
        FanMode.AUTO: 1,
        FanMode.LOW: 2,
        FanMode.MEDIUM: 3,
        FanMode.HIGH: 4,
    }

    def __init__(self, token: str, key: str):
        """
        Initialize the Remote class with the given token and key.

        Args:
            token (str): The API token for authentication.
            key (str): The API key for signing requests.
        """
        self.token = token
        self.key = key

        self.device_id: str = ""
        self.sent_state: str = ""
        self.sent_mode: Mode = Mode.NONE

    @staticmethod
    def format_send_state(state: str) -> str:
        """
        Format the send state string for logging.

        Args:
            state (str): The state string to format.

        Returns:
            str: The formatted state string.
        """

        def mode_gen(x):
            return (k for k, v in Remote.modes.items() if v == int(x))

        def fan_gen(x):
            return (k for k, v in Remote.fan_modes.items() if v == int(x))

        t, m, f, p = state.split(",")
        return (
            f"{state} -> temp={c_to_f(t)}, mode={next(mode_gen(m))}, fan={next(fan_gen(f))},"
            f" power={p}"
        )

    def get_device_info(self) -> List[Dict[str, str]]:
        """
        Get the list of devices from the SwitchBot API.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing device information.

        Raises:
            requests.RequestException: If the request to the API fails.
        """
        headers = self._get_headers()

        url = f"{self.endpoint}/devices"
        response = requests.get(url, headers=headers)

        if not response.ok:
            raise requests.RequestException(f"Unable to get device list: {response.reason}")

        return response.json()["body"]["infraredRemoteList"]

    def _get_headers(self) -> Dict[str, str]:
        """
        Generate the headers required for API requests.

        Returns:
            Dict[str, str]: A dictionary containing the headers.
        """
        nonce = uuid.uuid4()
        timestamp = int(round(time.time() * 1000))
        string_to_sign = bytes(f"{self.token}{timestamp}{nonce}", "utf-8")
        secret_bytes = bytes(self.key, "utf-8")

        sign = base64.b64encode(
            hmac.new(secret_bytes, msg=string_to_sign, digestmod=hashlib.sha256).digest()
        )

        return {
            "Authorization": self.token,
            "Content-Type": "application/json; charset=utf8",
            "t": str(timestamp),
            "sign": str(sign, "utf-8"),
            "nonce": str(nonce),
        }

    def post(
        self,
        device: Device,
        temp: float,
        mode: Mode = Mode.NONE,
        fan_mode: FanMode = FanMode.NONE,
    ) -> bool:
        """
        Send a command to the device to set its state.

        Args:
            device (Device): The device to control.
            temp (float, optional): The temperature to set. Defaults to None.
            mode (Mode, optional): The mode to set. Defaults to None.
            fan_mode (FanMode, optional): The fan mode to set. Defaults to None.

        Returns:
            bool: True if the command was sent successfully, False otherwise.
        """
        send_power = "off" if mode == Mode.OFF else "on"
        send_mode = self.modes[mode] or self.modes[self.sent_mode] or self.modes[Mode.FAN_ONLY]
        send_fan_mode = self.fan_modes[fan_mode]
        send_state = f"{round(temp)},{send_mode},{send_fan_mode},{send_power}"

        send_state_formatted = self.format_send_state(send_state)
        status = " (no send)" if send_state == self.sent_state else " \033[31mSENT\033[0m"

        LOG.info(f"Remote: {device.device_id}: {send_state_formatted}{status}")

        if send_state != self.sent_state:
            self.sent_mode = mode
            self.sent_state = send_state

            headers = self._get_headers()

            url = f"{self.endpoint}/devices/{device.device_id}/commands"
            data = {
                "commandType": "command",
                "command": "setAll",
                "parameter": send_state,
            }

            device.publish_send_state(send_state)

            response = requests.post(url, headers=headers, json=data)

            if not response.ok:
                LOG.critical(f"Remote: {response.reason}")
                LOG.critical(response.content)
                return False

        return True
