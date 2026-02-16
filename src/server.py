"""Main MCP server for home automation."""

import asyncio
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .config import settings
from .services.nest_client import NestClient
from .services.weather_client import WeatherClient
from .tools.thermostat import get_thermostat_tool_definitions, handle_thermostat_tool
from .tools.weather import get_weather_tool_definitions, handle_weather_tool

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class HomeAutomationServer:
    """Home Automation MCP Server."""

    def __init__(self):
        self.server = Server("home-automation-mcp")
        self.nest_client: NestClient | None = None
        self.weather_client: WeatherClient | None = None

    async def initialize(self):
        """Initialize API clients and register tools."""
        logger.info("Initializing Home Automation MCP Server")

        if settings.use_real_nest_api:
            logger.info("Initializing with real Google Nest API")
            self.nest_client = NestClient(
                use_real_api=True,
                google_project_id=settings.google_project_id,
                google_access_token=settings.google_access_token,
                google_refresh_token=settings.google_refresh_token,
                google_client_id=settings.google_client_id,
                google_client_secret=settings.google_client_secret,
            )
        else:
            logger.info(f"Connecting to dummy NEST API: {settings.nest_api_url}")
            self.nest_client = NestClient(base_url=settings.nest_api_url)

        if settings.weather_api_key:
            logger.info("Initializing Weather client")
            self.weather_client = WeatherClient(settings.weather_api_key)
        else:
            logger.warning("Weather API key not provided, weather tools will be disabled")

        self._register_tool_handlers()
        logger.info("Server initialization complete")

    def _register_tool_handlers(self):
        """Register unified tool handlers for all tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            tools = []
            tools.extend(get_thermostat_tool_definitions())
            if self.weather_client:
                tools.extend(get_weather_tool_definitions())
            logger.info(f"Registered {len(tools)} tools")
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            logger.debug(f"Tool called: {name} with arguments: {arguments}")

            thermostat_tools = {
                "list_thermostats",
                "get_thermostat_status",
                "set_thermostat_temperature",
                "get_thermostat_history",
            }
            weather_tools = {
                "get_current_weather",
                "get_weather_forecast",
                "get_weather_alerts",
            }

            if name in thermostat_tools:
                return await handle_thermostat_tool(name, arguments, self.nest_client)
            elif name in weather_tools:
                if not self.weather_client:
                    return [
                        TextContent(
                            type="text",
                            text="Weather tools are not available. "
                            "Please configure WEATHER_API_KEY.",
                        )
                    ]
                return await handle_weather_tool(name, arguments, self.weather_client)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up server resources")
        if self.nest_client:
            await self.nest_client.close()
        if self.weather_client:
            await self.weather_client.close()

    async def run(self):
        """Run the MCP server."""
        try:
            await self.initialize()
            async with stdio_server() as (read_stream, write_stream):
                logger.info("Server running on stdio")
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            raise
        finally:
            await self.cleanup()


async def main():
    """Main entry point."""
    server = HomeAutomationServer()
    await server.run()


def cli():
    """CLI entry point for the server."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
