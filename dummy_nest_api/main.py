"""Dummy NEST API Google Cloud Function.

This is a stateless mock API that simulates NEST thermostat operations
for testing the MCP server without requiring real NEST API credentials.
"""

import json
from datetime import datetime, timedelta
from typing import Any

import functions_framework
from flask import Request, jsonify
from pydantic import BaseModel, Field, ValidationError


# Data Models
class ThermostatStatus(BaseModel):
    """Thermostat status model."""

    id: str
    name: str
    current_temperature: float
    target_temperature: float
    mode: str = Field(..., pattern="^(heating|cooling|off)$")
    humidity: float
    status: str = "active"
    last_updated: str


class TemperatureRequest(BaseModel):
    """Temperature setting request model."""

    temperature: float = Field(..., ge=50, le=90)
    unit: str = Field(default="fahrenheit", pattern="^(fahrenheit|celsius)$")


class TemperatureResponse(BaseModel):
    """Temperature setting response model."""

    success: bool
    thermostat_id: str
    previous_temperature: float
    new_temperature: float
    unit: str
    estimated_time_minutes: int
    timestamp: str


# Mock Data
MOCK_THERMOSTATS = {
    "thermostat-1": {
        "id": "thermostat-1",
        "name": "Living Room",
        "current_temperature": 72.0,
        "target_temperature": 70.0,
        "mode": "cooling",
        "humidity": 45.0,
        "status": "active",
    },
    "thermostat-2": {
        "id": "thermostat-2",
        "name": "Bedroom",
        "current_temperature": 68.0,
        "target_temperature": 68.0,
        "mode": "heating",
        "humidity": 50.0,
        "status": "active",
    },
    "thermostat-3": {
        "id": "thermostat-3",
        "name": "Office",
        "current_temperature": 74.0,
        "target_temperature": 72.0,
        "mode": "off",
        "humidity": 42.0,
        "status": "active",
    },
}


def generate_temperature_history(thermostat_id: str, hours: int = 24) -> list[dict[str, Any]]:
    """Generate mock temperature history data."""
    history = []
    base_temp = MOCK_THERMOSTATS.get(thermostat_id, {}).get("current_temperature", 70.0)

    for i in range(hours):
        timestamp = datetime.utcnow() - timedelta(hours=hours - i)
        # Add some random variation
        temp_variation = (i % 3) - 1  # -1, 0, or 1 degree variation
        history.append({
            "timestamp": timestamp.isoformat() + "Z",
            "temperature": base_temp + temp_variation,
            "humidity": 45 + (i % 5),
        })

    return history


@functions_framework.http
def thermostat_handler(request: Request):
    """HTTP Cloud Function entry point."""

    # Enable CORS
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return ("", 204, headers)

    headers = {"Access-Control-Allow-Origin": "*"}

    try:
        path = request.path.strip("/")
        parts = path.split("/")

        # GET /thermostats - List all thermostats
        if request.method == "GET" and path == "thermostats":
            thermostats = []
            for t_id, t_data in MOCK_THERMOSTATS.items():
                data = t_data.copy()
                data["last_updated"] = datetime.utcnow().isoformat() + "Z"
                thermostats.append(ThermostatStatus(**data).model_dump())

            return jsonify({"thermostats": thermostats, "count": len(thermostats)}), 200, headers

        # GET /thermostats/{id} - Get specific thermostat
        if request.method == "GET" and len(parts) == 2 and parts[0] == "thermostats":
            thermostat_id = parts[1]

            if thermostat_id not in MOCK_THERMOSTATS:
                return jsonify({"error": f"Thermostat {thermostat_id} not found"}), 404, headers

            data = MOCK_THERMOSTATS[thermostat_id].copy()
            data["last_updated"] = datetime.utcnow().isoformat() + "Z"
            thermostat = ThermostatStatus(**data)

            return jsonify(thermostat.model_dump()), 200, headers

        # POST /thermostats/{id}/temperature - Set temperature
        if request.method == "POST" and len(parts) == 3 and parts[0] == "thermostats" and parts[2] == "temperature":
            thermostat_id = parts[1]

            if thermostat_id not in MOCK_THERMOSTATS:
                return jsonify({"error": f"Thermostat {thermostat_id} not found"}), 404, headers

            # Parse request body
            try:
                request_data = request.get_json()
                if not request_data:
                    return jsonify({"error": "Request body is required"}), 400, headers

                temp_request = TemperatureRequest(**request_data)
            except ValidationError as e:
                return jsonify({"error": "Invalid request", "details": e.errors()}), 400, headers

            # Create response
            previous_temp = MOCK_THERMOSTATS[thermostat_id]["target_temperature"]
            current_temp = MOCK_THERMOSTATS[thermostat_id]["current_temperature"]

            # Estimate time based on temperature difference
            temp_diff = abs(temp_request.temperature - current_temp)
            estimated_time = int(temp_diff * 5)  # ~5 minutes per degree

            response = TemperatureResponse(
                success=True,
                thermostat_id=thermostat_id,
                previous_temperature=previous_temp,
                new_temperature=temp_request.temperature,
                unit=temp_request.unit,
                estimated_time_minutes=estimated_time,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

            return jsonify(response.model_dump()), 200, headers

        # GET /thermostats/{id}/history - Get temperature history
        if request.method == "GET" and len(parts) == 3 and parts[0] == "thermostats" and parts[2] == "history":
            thermostat_id = parts[1]

            if thermostat_id not in MOCK_THERMOSTATS:
                return jsonify({"error": f"Thermostat {thermostat_id} not found"}), 404, headers

            hours = int(request.args.get("hours", 24))
            history = generate_temperature_history(thermostat_id, min(hours, 168))  # Max 1 week

            return jsonify({
                "thermostat_id": thermostat_id,
                "history": history,
                "count": len(history),
            }), 200, headers

        # Unknown endpoint
        return jsonify({"error": "Endpoint not found", "path": path}), 404, headers

    except Exception as e:
        return jsonify({"error": "Internal server error", "message": str(e)}), 500, headers
