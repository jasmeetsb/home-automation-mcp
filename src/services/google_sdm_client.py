"""Google Smart Device Management API client for real Nest devices."""

import logging
from pathlib import Path

import httpx
from dotenv import set_key

logger = logging.getLogger(__name__)


def fahrenheit_to_celsius(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (f - 32) * 5.0 / 9.0


def celsius_to_fahrenheit(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (c * 9.0 / 5.0) + 32


class GoogleSDMClient:
    """Client for Google Smart Device Management API."""

    API_BASE = "https://smartdevicemanagement.googleapis.com/v1"
    TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"

    def __init__(
        self,
        project_id: str,
        access_token: str,
        refresh_token: str = "",
        client_id: str = "",
        client_secret: str = "",
        timeout: float = 30.0,
    ):
        self.project_id = project_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict = None,
        retry_on_401: bool = True,
    ) -> dict:
        """Make authenticated API request with automatic token refresh on 401."""
        url = f"{self.API_BASE}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            if method == "GET":
                response = await self._client.get(url, headers=headers)
            elif method == "POST":
                response = await self._client.post(url, headers=headers, json=json_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401 and retry_on_401 and self.refresh_token:
                logger.info("Access token expired. Refreshing...")
                await self._refresh_access_token()
                return await self._make_request(method, endpoint, json_data, retry_on_401=False)
            logger.error(f"API request failed: {e.response.status_code} - {e.response.text}")
            raise

    async def _refresh_access_token(self):
        """Refresh the access token using refresh token and persist to .env."""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise ValueError("Missing credentials for token refresh")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }

        response = await self._client.post(self.TOKEN_URL, data=payload)
        response.raise_for_status()
        data = response.json()

        new_access_token = data.get("access_token")
        if not new_access_token:
            raise ValueError("No access token in refresh response")

        self.access_token = new_access_token

        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            set_key(str(env_path), "GOOGLE_ACCESS_TOKEN", new_access_token)
            logger.info("Access token refreshed and saved to .env")
        else:
            logger.warning("Access token refreshed but .env not found to persist")

    async def list_devices(self) -> list[dict]:
        """List all devices in the project."""
        endpoint = f"enterprises/{self.project_id}/devices"
        data = await self._make_request("GET", endpoint)
        return data.get("devices", [])

    async def get_device(self, device_id: str) -> dict:
        """Get a specific device by its full ID path."""
        device_id = device_id.lstrip("/")
        return await self._make_request("GET", device_id)

    async def set_temperature(self, device_id: str, temperature_celsius: float) -> dict:
        """Set thermostat target temperature, using the appropriate command for the current mode."""
        device = await self.get_device(device_id)
        traits = device.get("traits", {})
        mode_trait = traits.get("sdm.devices.traits.ThermostatMode", {})
        current_mode = mode_trait.get("mode", "HEAT")

        if current_mode == "COOL":
            payload = {
                "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetCool",
                "params": {"coolCelsius": temperature_celsius},
            }
        elif current_mode == "HEATCOOL":
            payload = {
                "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetRange",
                "params": {
                    "heatCelsius": temperature_celsius - 1,
                    "coolCelsius": temperature_celsius + 1,
                },
            }
        else:
            payload = {
                "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetHeat",
                "params": {"heatCelsius": temperature_celsius},
            }

        device_id = device_id.lstrip("/")
        return await self._make_request("POST", f"{device_id}:executeCommand", payload)

    async def set_mode(self, device_id: str, mode: str) -> dict:
        """Set thermostat mode (HEAT, COOL, HEATCOOL, OFF)."""
        payload = {
            "command": "sdm.devices.commands.ThermostatMode.SetMode",
            "params": {"mode": mode},
        }
        device_id = device_id.lstrip("/")
        return await self._make_request("POST", f"{device_id}:executeCommand", payload)
