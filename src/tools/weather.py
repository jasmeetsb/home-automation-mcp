"""MCP tools for weather information."""

import logging
from datetime import datetime
from typing import Any

from mcp.types import TextContent, Tool

from ..services.weather_client import WeatherClient

logger = logging.getLogger(__name__)


def get_weather_tool_definitions() -> list[Tool]:
    """Get weather tool definitions for MCP registration."""
    return [
        Tool(
            name="get_current_weather",
            description="Get current weather conditions for a location",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name (e.g., 'London', 'New York')",
                    },
                    "units": {
                        "type": "string",
                        "enum": ["imperial", "metric", "standard"],
                        "description": "Units system (imperial=°F, metric=°C)",
                        "default": "imperial",
                    },
                },
                "required": ["location"],
            },
        ),
        Tool(
            name="get_weather_forecast",
            description="Get weather forecast for a location",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days (1-5)",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 5,
                    },
                    "units": {
                        "type": "string",
                        "enum": ["imperial", "metric", "standard"],
                        "description": "Units system",
                        "default": "imperial",
                    },
                },
                "required": ["location"],
            },
        ),
        Tool(
            name="get_weather_alerts",
            description="Get weather alerts for coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude",
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude",
                    },
                },
                "required": ["latitude", "longitude"],
            },
        ),
    ]


async def handle_weather_tool(
    name: str, arguments: dict[str, Any], weather_client: WeatherClient
) -> list[TextContent]:
    """Handle tool calls for weather."""
    try:
        if name == "get_current_weather":
            return await _get_current_weather(weather_client, arguments)
        elif name == "get_weather_forecast":
            return await _get_weather_forecast(weather_client, arguments)
        elif name == "get_weather_alerts":
            return await _get_weather_alerts(weather_client, arguments)
        else:
            raise ValueError(f"Unknown weather tool: {name}")
    except Exception as e:
        logger.error(f"Error executing weather tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {e!s}")]


async def _get_current_weather(
    weather_client: WeatherClient, arguments: dict[str, Any]
) -> list[TextContent]:
    location = arguments["location"]
    units = arguments.get("units", "imperial")

    weather = await weather_client.get_current_weather(location, units)

    unit_symbol = "°F" if units == "imperial" else "°C" if units == "metric" else "K"
    speed_unit = "mph" if units == "imperial" else "m/s"

    dt = datetime.fromtimestamp(weather.timestamp)
    result = f"**Current Weather in {weather.location}**\n\n"
    result += f"- **Temperature:** {weather.temperature}{unit_symbol}\n"
    result += f"- **Feels Like:** {weather.feels_like}{unit_symbol}\n"
    result += f"- **Description:** {weather.description.title()}\n"
    result += f"- **Humidity:** {weather.humidity}%\n"
    result += f"- **Pressure:** {weather.pressure} hPa\n"
    result += f"- **Wind Speed:** {weather.wind_speed} {speed_unit}\n"
    result += f"- **Cloud Cover:** {weather.clouds}%\n"
    result += f"- **Updated:** {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"

    return [TextContent(type="text", text=result)]


async def _get_weather_forecast(
    weather_client: WeatherClient, arguments: dict[str, Any]
) -> list[TextContent]:
    location = arguments["location"]
    days = arguments.get("days", 3)
    units = arguments.get("units", "imperial")

    forecasts = await weather_client.get_forecast(location, units, days)

    unit_symbol = "°F" if units == "imperial" else "°C" if units == "metric" else "K"
    speed_unit = "mph" if units == "imperial" else "m/s"

    result = f"**Weather Forecast for {location}** ({days} days)\n\n"

    current_day = None
    for forecast in forecasts:
        dt = datetime.fromtimestamp(forecast.timestamp)
        day = dt.strftime("%A, %B %d")

        if day != current_day:
            current_day = day
            result += f"\n**{day}:**\n"

        time = dt.strftime("%I:%M %p")
        result += f"- {time}: {forecast.temperature}{unit_symbol}, "
        result += f"{forecast.description}, "
        result += f"Humidity: {forecast.humidity}%, "
        result += f"Wind: {forecast.wind_speed} {speed_unit}"

        if forecast.pop > 0:
            result += f", Precipitation: {int(forecast.pop * 100)}%"

        result += "\n"

    return [TextContent(type="text", text=result)]


async def _get_weather_alerts(
    weather_client: WeatherClient, arguments: dict[str, Any]
) -> list[TextContent]:
    lat = arguments["latitude"]
    lon = arguments["longitude"]

    alerts = await weather_client.get_alerts(lat, lon)

    if not alerts:
        return [TextContent(type="text", text=f"No weather alerts for coordinates {lat}, {lon}")]

    result = f"**Weather Alerts** ({len(alerts)} active)\n\n"

    for i, alert in enumerate(alerts, 1):
        start_dt = datetime.fromtimestamp(alert.start)
        end_dt = datetime.fromtimestamp(alert.end)
        result += f"**Alert {i}: {alert.event}**\n"
        result += f"- **From:** {start_dt.strftime('%Y-%m-%d %H:%M')}\n"
        result += f"- **To:** {end_dt.strftime('%Y-%m-%d %H:%M')}\n"
        result += f"- **Source:** {alert.sender_name}\n"
        result += f"- **Description:** {alert.description}\n\n"

    return [TextContent(type="text", text=result)]
