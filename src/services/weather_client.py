"""Weather service client using OpenWeatherMap API."""

import logging

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CurrentWeather(BaseModel):
    """Current weather data."""

    location: str
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    description: str
    wind_speed: float
    clouds: int
    timestamp: int


class ForecastEntry(BaseModel):
    """Weather forecast entry."""

    timestamp: int
    temperature: float
    feels_like: float
    humidity: int
    description: str
    pop: float
    wind_speed: float


class WeatherAlert(BaseModel):
    """Weather alert."""

    event: str
    start: int
    end: int
    description: str
    sender_name: str


class WeatherClient:
    """Client for OpenWeatherMap API."""

    def __init__(self, api_key: str, timeout: float = 30.0):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_current_weather(
        self,
        location: str,
        units: str = "imperial",
    ) -> CurrentWeather:
        """Get current weather for a location."""
        logger.info(f"Fetching current weather for: {location}")

        params = {"q": location, "appid": self.api_key, "units": units}
        response = await self._client.get(f"{self.base_url}/weather", params=params)
        response.raise_for_status()
        data = response.json()

        return CurrentWeather(
            location=data["name"],
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            humidity=data["main"]["humidity"],
            pressure=data["main"]["pressure"],
            description=data["weather"][0]["description"],
            wind_speed=data["wind"]["speed"],
            clouds=data["clouds"]["all"],
            timestamp=data["dt"],
        )

    async def get_forecast(
        self,
        location: str,
        units: str = "imperial",
        days: int = 5,
    ) -> list[ForecastEntry]:
        """Get weather forecast for a location (3-hour intervals)."""
        logger.info(f"Fetching {days}-day forecast for: {location}")

        params = {
            "q": location,
            "appid": self.api_key,
            "units": units,
            "cnt": min(days * 8, 40),
        }
        response = await self._client.get(f"{self.base_url}/forecast", params=params)
        response.raise_for_status()
        data = response.json()

        return [
            ForecastEntry(
                timestamp=item["dt"],
                temperature=item["main"]["temp"],
                feels_like=item["main"]["feels_like"],
                humidity=item["main"]["humidity"],
                description=item["weather"][0]["description"],
                pop=item.get("pop", 0.0),
                wind_speed=item["wind"]["speed"],
            )
            for item in data["list"]
        ]

    async def get_alerts(
        self,
        lat: float,
        lon: float,
    ) -> list[WeatherAlert] | None:
        """Get weather alerts for coordinates (requires OneCall API)."""
        logger.info(f"Fetching weather alerts for: {lat}, {lon}")

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "exclude": "current,minutely,hourly,daily",
        }
        response = await self._client.get(
            "https://api.openweathermap.org/data/3.0/onecall", params=params
        )
        response.raise_for_status()
        data = response.json()

        alerts_data = data.get("alerts", [])
        if not alerts_data:
            return None

        return [
            WeatherAlert(
                event=a["event"],
                start=a["start"],
                end=a["end"],
                description=a["description"],
                sender_name=a["sender_name"],
            )
            for a in alerts_data
        ]
