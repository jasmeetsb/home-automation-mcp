#!/bin/bash

# Run the dummy NEST API using uv (no venv activation needed!)

echo "Starting Dummy NEST API with uv on port 8081..."
echo "Press Ctrl+C to stop"
echo ""

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Run functions-framework
# Note: Dependencies should be installed first with: uv pip install functions-framework pydantic flask
uv run functions-framework --target=thermostat_handler --port=8081 --debug
