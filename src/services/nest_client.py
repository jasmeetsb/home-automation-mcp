"""NEST API client for thermostat operations.

Supports both a dummy REST API and the real Google SDM API,
toggled by the use_real_api flag.
"""

import logging
from datetime import datetime

import httpx
from pydantic import BaseModel

from .google_sdm_client import GoogleSDMClient, celsius_to_fahrenheit, fahrenheit_to_celsius

logger = logging.getLogger(__name__)


class ThermostatStatus(BaseModel):
    """Thermostat status model."""

    id: str
    name: str
    current_temperature: float
    target_temperature: float
    mode: str
    humidity: float
    status: str
    last_updated: str


class TemperatureSetResult(BaseModel):
    """Result of setting temperature."""

    success: bool
    thermostat_id: str
    previous_temperature: float
    new_temperature: float
    unit: str
    estimated_time_minutes: int
    timestamp: str


class HistoryEntry(BaseModel):
    """Temperature history entry."""

    timestamp: str
    temperature: float
    humidity: float


class NestClient:
    """Client for interacting with NEST API (dummy or real Google SDM)."""

    def __init__(
        self,
        base_url: str = None,
        timeout: float = 30.0,
        use_real_api: bool = False,
        google_project_id: str = None,
        google_access_token: str = None,
        google_refresh_token: str = None,
        google_client_id: str = None,
        google_client_secret: str = None,
    ):
        self.use_real_api = use_real_api
        self.timeout = timeout

        if use_real_api:
            if not all([google_project_id, google_access_token]):
                raise ValueError("Google credentials required for real API")

            logger.info("Initializing real Google SDM API client")
            self.sdm_client = GoogleSDMClient(
                project_id=google_project_id,
                access_token=google_access_token,
                refresh_token=google_refresh_token or "",
                client_id=google_client_id or "",
                client_secret=google_client_secret or "",
                timeout=timeout,
            )
            self._client = None
        else:
            if not base_url:
                raise ValueError("Base URL required for dummy API")

            logger.info(f"Initializing dummy API client with URL: {base_url}")
            self.base_url = base_url.rstrip("/")
            self._client = httpx.AsyncClient(timeout=timeout)
            self.sdm_client = None

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
        if self.sdm_client:
            await self.sdm_client.close()

    def _parse_sdm_device(self, device: dict) -> ThermostatStatus:
        """Parse Google SDM device response into ThermostatStatus."""
        device_id = device.get("name", "").split("/")[-1] or device.get("name", "unknown")
        traits = device.get("traits", {})

        info_trait = traits.get("sdm.devices.traits.Info", {})
        name = info_trait.get("customName", device_id)

        temp_trait = traits.get("sdm.devices.traits.Temperature", {})
        current_temp_c = temp_trait.get("ambientTemperatureCelsius", 20.0)
        current_temp_f = celsius_to_fahrenheit(current_temp_c)

        humidity_trait = traits.get("sdm.devices.traits.Humidity", {})
        humidity = humidity_trait.get("ambientHumidityPercent", 50.0)

        mode_trait = traits.get("sdm.devices.traits.ThermostatMode", {})
        mode_map = {"HEAT": "heating", "COOL": "cooling", "HEATCOOL": "auto", "OFF": "off"}
        mode = mode_map.get(mode_trait.get("mode", "OFF"), "off")

        setpoint_trait = traits.get("sdm.devices.traits.ThermostatTemperatureSetpoint", {})
        if mode == "cooling" and "coolCelsius" in setpoint_trait:
            target_temp_c = setpoint_trait["coolCelsius"]
        elif mode == "heating" and "heatCelsius" in setpoint_trait:
            target_temp_c = setpoint_trait["heatCelsius"]
        elif mode == "auto":
            heat_c = setpoint_trait.get("heatCelsius", 20.0)
            cool_c = setpoint_trait.get("coolCelsius", 25.0)
            target_temp_c = (heat_c + cool_c) / 2
        else:
            target_temp_c = current_temp_c

        target_temp_f = celsius_to_fahrenheit(target_temp_c)

        hvac_trait = traits.get("sdm.devices.traits.ThermostatHvac", {})
        hvac_status = hvac_trait.get("status", "OFF")
        status = "active" if hvac_status != "OFF" else "idle"

        return ThermostatStatus(
            id=device.get("name", device_id),
            name=name,
            current_temperature=round(current_temp_f, 1),
            target_temperature=round(target_temp_f, 1),
            mode=mode,
            humidity=round(humidity, 1),
            status=status,
            last_updated=datetime.utcnow().isoformat() + "Z",
        )

    async def list_thermostats(self) -> list[ThermostatStatus]:
        """List all available thermostats."""
        if self.use_real_api:
            logger.info("Fetching real thermostats from Google SDM API")
            devices = await self.sdm_client.list_devices()
            thermostats = [
                self._parse_sdm_device(d)
                for d in devices
                if "THERMOSTAT" in d.get("type", "").upper()
            ]
            logger.info(f"Retrieved {len(thermostats)} real thermostats")
            return thermostats
        else:
            logger.info("Fetching thermostat list from dummy API")
            response = await self._client.get(f"{self.base_url}/thermostats")
            response.raise_for_status()
            data = response.json()
            return [ThermostatStatus(**t) for t in data.get("thermostats", [])]

    async def get_thermostat(self, thermostat_id: str) -> ThermostatStatus:
        """Get status of a specific thermostat."""
        if self.use_real_api:
            logger.info(f"Fetching real thermostat: {thermostat_id}")
            device = await self.sdm_client.get_device(thermostat_id)
            return self._parse_sdm_device(device)
        else:
            logger.info(f"Fetching dummy thermostat: {thermostat_id}")
            response = await self._client.get(f"{self.base_url}/thermostats/{thermostat_id}")
            response.raise_for_status()
            return ThermostatStatus(**response.json())

    async def set_temperature(
        self,
        thermostat_id: str,
        temperature: float,
        unit: str = "fahrenheit",
    ) -> TemperatureSetResult:
        """Set target temperature for a thermostat."""
        if self.use_real_api:
            logger.info(
                f"Setting real thermostat {thermostat_id} to {temperature}°{unit[0].upper()}"
            )
            current_device = await self.sdm_client.get_device(thermostat_id)
            current_status = self._parse_sdm_device(current_device)
            previous_temp = current_status.target_temperature

            if unit == "fahrenheit":
                temp_celsius = fahrenheit_to_celsius(temperature)
            else:
                temp_celsius = temperature
            await self.sdm_client.set_temperature(thermostat_id, temp_celsius)

            return TemperatureSetResult(
                success=True,
                thermostat_id=thermostat_id,
                previous_temperature=previous_temp,
                new_temperature=temperature,
                unit=unit,
                estimated_time_minutes=5,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        else:
            logger.info(
                f"Setting dummy thermostat {thermostat_id} to {temperature}°{unit[0].upper()}"
            )
            response = await self._client.post(
                f"{self.base_url}/thermostats/{thermostat_id}/temperature",
                json={"temperature": temperature, "unit": unit},
            )
            response.raise_for_status()
            return TemperatureSetResult(**response.json())

    async def get_history(
        self,
        thermostat_id: str,
        hours: int = 24,
    ) -> list[HistoryEntry]:
        """Get temperature history for a thermostat."""
        if self.use_real_api:
            logger.warning("Temperature history not available in Google SDM API")
            device = await self.sdm_client.get_device(thermostat_id)
            status = self._parse_sdm_device(device)
            return [
                HistoryEntry(
                    timestamp=status.last_updated,
                    temperature=status.current_temperature,
                    humidity=status.humidity,
                )
            ]
        else:
            logger.info(f"Fetching history for dummy thermostat {thermostat_id} ({hours} hours)")
            response = await self._client.get(
                f"{self.base_url}/thermostats/{thermostat_id}/history",
                params={"hours": hours},
            )
            response.raise_for_status()
            data = response.json()
            return [HistoryEntry(**entry) for entry in data.get("history", [])]
