#!/bin/bash

# Run the dummy NEST API locally for testing

echo "Starting Dummy NEST API locally on port 8081..."
echo "Press Ctrl+C to stop"
echo ""

source .venv/bin/activate
functions-framework --target=thermostat_handler --port=8081 --debug
