"""MCP tools for thermostat control."""

import logging
from typing import Any

from mcp.types import TextContent, Tool

from ..services.nest_client import NestClient

logger = logging.getLogger(__name__)

# Cache to map short IDs and numbers to full device IDs
_thermostat_id_cache: dict[str, str] = {}


def _shorten_device_id(device_id: str) -> str:
    """Shorten a long device ID for display (last 8 chars)."""
    if "/" in device_id:
        device_part = device_id.split("/")[-1]
        if len(device_part) > 8:
            return f"...{device_part[-8:]}"
        return device_part
    if len(device_id) > 12:
        return f"...{device_id[-8:]}"
    return device_id


def _cache_thermostat_id(full_id: str, index: int) -> None:
    """Cache mappings from short ID, number, and aliases to full device ID."""
    short_id = _shorten_device_id(full_id)
    _thermostat_id_cache[short_id] = full_id
    _thermostat_id_cache[short_id.lstrip(".")] = full_id
    _thermostat_id_cache[str(index)] = full_id
    _thermostat_id_cache[f"thermostat-{index}"] = full_id
    _thermostat_id_cache[f"thermostat {index}"] = full_id
    _thermostat_id_cache[full_id] = full_id


def _resolve_thermostat_id(thermostat_id: str) -> str:
    """Resolve a thermostat ID (short, number, or full) to the full device ID."""
    normalized = thermostat_id.strip().lower()

    if thermostat_id in _thermostat_id_cache:
        return _thermostat_id_cache[thermostat_id]

    for key, full_id in _thermostat_id_cache.items():
        if key.lower() == normalized:
            return full_id

    if "enterprises" in thermostat_id or "devices" in thermostat_id:
        return thermostat_id

    for key, full_id in _thermostat_id_cache.items():
        if key.endswith(thermostat_id.lstrip(".")) and len(thermostat_id) >= 4:
            return full_id

    logger.warning(f"Could not resolve thermostat ID: {thermostat_id}")
    return thermostat_id


def get_thermostat_tool_definitions() -> list[Tool]:
    """Get thermostat tool definitions for MCP registration."""
    return [
        Tool(
            name="list_thermostats",
            description="List all available thermostats in the home",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_thermostat_status",
            description="Get the current status of a specific thermostat",
            inputSchema={
                "type": "object",
                "properties": {
                    "thermostat_id": {
                        "type": "string",
                        "description": "Thermostat number (e.g., '1', '2') or short ID",
                    },
                },
                "required": ["thermostat_id"],
            },
        ),
        Tool(
            name="set_thermostat_temperature",
            description="Set the target temperature for a thermostat",
            inputSchema={
                "type": "object",
                "properties": {
                    "thermostat_id": {
                        "type": "string",
                        "description": "Thermostat number (e.g., '1', '2') or short ID",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Target temperature (50-90 for Fahrenheit)",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["fahrenheit", "celsius"],
                        "description": "Temperature unit",
                        "default": "fahrenheit",
                    },
                },
                "required": ["thermostat_id", "temperature"],
            },
        ),
        Tool(
            name="get_thermostat_history",
            description="Get temperature history for a thermostat",
            inputSchema={
                "type": "object",
                "properties": {
                    "thermostat_id": {
                        "type": "string",
                        "description": "Thermostat number (e.g., '1', '2') or short ID",
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours of history (default: 24, max: 168)",
                        "default": 24,
                        "minimum": 1,
                        "maximum": 168,
                    },
                },
                "required": ["thermostat_id"],
            },
        ),
    ]


async def handle_thermostat_tool(
    name: str, arguments: dict[str, Any], nest_client: NestClient
) -> list[TextContent]:
    """Handle tool calls for thermostats."""
    try:
        if name == "list_thermostats":
            return await _list_thermostats(nest_client)
        elif name == "get_thermostat_status":
            return await _get_thermostat_status(nest_client, arguments)
        elif name == "set_thermostat_temperature":
            return await _set_thermostat_temperature(nest_client, arguments)
        elif name == "get_thermostat_history":
            return await _get_thermostat_history(nest_client, arguments)
        else:
            raise ValueError(f"Unknown thermostat tool: {name}")
    except Exception as e:
        logger.error(f"Error executing thermostat tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {e!s}")]


async def _list_thermostats(nest_client: NestClient) -> list[TextContent]:
    thermostats = await nest_client.list_thermostats()

    if not thermostats:
        return [TextContent(type="text", text="No thermostats found.")]

    result = "**Available Thermostats:**\n\n"
    for idx, t in enumerate(thermostats, 1):
        _cache_thermostat_id(t.id, idx)
        short_id = _shorten_device_id(t.id)
        display_name = t.name if t.name else f"Thermostat {idx}"
        result += f"- **{display_name}** (use `{idx}` or `{short_id}`)\n"
        result += f"  - Current: {t.current_temperature}°F\n"
        result += f"  - Target: {t.target_temperature}°F\n"
        result += f"  - Mode: {t.mode}\n"
        result += f"  - Humidity: {t.humidity}%\n"
        result += f"  - Status: {t.status}\n\n"

    return [TextContent(type="text", text=result)]


async def _get_thermostat_status(
    nest_client: NestClient, arguments: dict[str, Any]
) -> list[TextContent]:
    thermostat_id = arguments["thermostat_id"]
    full_id = _resolve_thermostat_id(thermostat_id)
    thermostat = await nest_client.get_thermostat(full_id)

    short_id = _shorten_device_id(thermostat.id)
    display_name = thermostat.name if thermostat.name else "Thermostat"
    result = f"**{display_name}** (ID: `{short_id}`)\n\n"
    result += f"- **Current Temperature:** {thermostat.current_temperature}°F\n"
    result += f"- **Target Temperature:** {thermostat.target_temperature}°F\n"
    result += f"- **Mode:** {thermostat.mode}\n"
    result += f"- **Humidity:** {thermostat.humidity}%\n"
    result += f"- **Status:** {thermostat.status}\n"
    result += f"- **Last Updated:** {thermostat.last_updated}\n"

    return [TextContent(type="text", text=result)]


async def _set_thermostat_temperature(
    nest_client: NestClient, arguments: dict[str, Any]
) -> list[TextContent]:
    thermostat_id = arguments["thermostat_id"]
    temperature = arguments["temperature"]
    unit = arguments.get("unit", "fahrenheit")

    full_id = _resolve_thermostat_id(thermostat_id)
    result_data = await nest_client.set_temperature(full_id, temperature, unit)

    short_id = _shorten_device_id(result_data.thermostat_id)
    result = "**Temperature Set Successfully**\n\n"
    result += f"- **Thermostat:** `{short_id}`\n"
    result += f"- **Previous:** {result_data.previous_temperature}°{unit[0].upper()}\n"
    result += f"- **New Target:** {result_data.new_temperature}°{unit[0].upper()}\n"
    result += f"- **Estimated Time:** {result_data.estimated_time_minutes} minutes\n"

    return [TextContent(type="text", text=result)]


async def _get_thermostat_history(
    nest_client: NestClient, arguments: dict[str, Any]
) -> list[TextContent]:
    thermostat_id = arguments["thermostat_id"]
    hours = arguments.get("hours", 24)

    full_id = _resolve_thermostat_id(thermostat_id)
    history = await nest_client.get_history(full_id, hours)

    if not history:
        return [TextContent(type="text", text="No history data available.")]

    temps = [entry.temperature for entry in history]
    avg_temp = sum(temps) / len(temps)

    result = f"**Temperature History** ({len(history)} entries, last {hours} hours)\n\n"
    result += "**Summary:**\n"
    result += f"- Average: {avg_temp:.1f}°F\n"
    result += f"- Min: {min(temps):.1f}°F\n"
    result += f"- Max: {max(temps):.1f}°F\n\n"

    result += "**Recent Readings:**\n"
    for entry in history[-10:]:
        result += f"- {entry.timestamp}: {entry.temperature}°F, {entry.humidity}% humidity\n"

    if len(history) > 10:
        result += f"\n_(Showing last 10 of {len(history)} entries)_\n"

    return [TextContent(type="text", text=result)]
