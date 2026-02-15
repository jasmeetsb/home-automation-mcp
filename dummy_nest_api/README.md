# Dummy NEST API

A stateless mock Google Cloud Function that simulates NEST thermostat API for testing.

## Endpoints

### GET /thermostats
List all available thermostats.

**Response:**
```json
{
  "thermostats": [...],
  "count": 3
}
```

### GET /thermostats/{id}
Get specific thermostat status.

**Response:**
```json
{
  "id": "thermostat-1",
  "name": "Living Room",
  "current_temperature": 72.0,
  "target_temperature": 70.0,
  "mode": "cooling",
  "humidity": 45.0,
  "status": "active",
  "last_updated": "2024-10-28T12:00:00Z"
}
```

### POST /thermostats/{id}/temperature
Set target temperature.

**Request:**
```json
{
  "temperature": 72,
  "unit": "fahrenheit"
}
```

**Response:**
```json
{
  "success": true,
  "thermostat_id": "thermostat-1",
  "previous_temperature": 70,
  "new_temperature": 72,
  "unit": "fahrenheit",
  "estimated_time_minutes": 15,
  "timestamp": "2024-10-28T12:00:00Z"
}
```

### GET /thermostats/{id}/history
Get temperature history.

**Query Parameters:**
- `hours` (optional): Number of hours of history (default: 24, max: 168)

**Response:**
```json
{
  "thermostat_id": "thermostat-1",
  "history": [...],
  "count": 24
}
```

## Running Locally

There are multiple ways to run the dummy NEST API locally. Choose the one that works best for you!

### Option 1: Using `uv run` (Recommended ⭐)

**No virtual environment activation needed!**

```bash
uv run functions-framework --target=thermostat_handler --port=8081 --debug
```

**Or use the convenience script:**
```bash
./run_with_uv.sh
```

**Advantages:**
- ✅ No need to activate virtual environment
- ✅ uv handles dependencies automatically
- ✅ Cleanest and most modern approach
- ✅ Works even if you haven't created a venv yet

### Option 2: Using Virtual Environment (Traditional)

```bash
source .venv/bin/activate
functions-framework --target=thermostat_handler --port=8081 --debug
```

**Or use the convenience script:**
```bash
./run_local.sh
```

**Advantages:**
- ✅ Traditional approach
- ✅ Works without uv installed
- ✅ Explicit about which environment you're using

### Option 3: Direct Python Invocation

```bash
uv run python -m functions_framework --target=thermostat_handler --port=8081 --debug
```

**Advantages:**
- ✅ Most explicit
- ✅ Shows exactly what's being run

### Comparison

| Method | Command | Requires venv? | Requires uv? |
|--------|---------|----------------|--------------|
| **uv run** | `uv run functions-framework ...` | ❌ No | ✅ Yes |
| **venv** | `source .venv/bin/activate && functions-framework ...` | ✅ Yes | ❌ No |
| **Direct** | `uv run python -m functions_framework ...` | ❌ No | ✅ Yes |

## Command Line Options

Common options you can add to any method:

```bash
--port=9000              # Change port (default: 8080)
--debug                  # Enable debug mode (auto-reload on file changes)
--source=main.py         # Specify source file
--target=thermostat_handler  # Specify function name
--host=0.0.0.0          # Set host (default: localhost)
```

**Examples:**

```bash
# Run on different port
uv run functions-framework --target=thermostat_handler --port=9000

# Run without debug (production mode)
uv run functions-framework --target=thermostat_handler --port=8081

# Run and expose to network
uv run functions-framework --target=thermostat_handler --port=8081 --host=0.0.0.0
```

## Testing the API

Once running (any method), test with:

```bash
# From project root
cd ..
./test_dummy_api.sh

# Or manual tests:
curl http://localhost:8081/thermostats
curl http://localhost:8081/thermostats/thermostat-1

# Set temperature
curl -X POST http://localhost:8081/thermostats/thermostat-1/temperature \
  -H "Content-Type: application/json" \
  -d '{"temperature": 72, "unit": "fahrenheit"}'

# Get history
curl http://localhost:8081/thermostats/thermostat-1/history?hours=12
```

## Installation & Setup

### First Time Setup

**Install dependencies:**

```bash
# Using uv (recommended)
uv pip install functions-framework pydantic flask

# Or using pip with venv
uv venv
source .venv/bin/activate
pip install functions-framework pydantic flask
```

### Recommended Workflow

For the cleanest workflow, use `uv run`:

1. **Install dependencies once:**
   ```bash
   uv pip install functions-framework pydantic flask
   ```

2. **Run whenever needed:**
   ```bash
   ./run_with_uv.sh
   ```

3. **No activation needed!** uv handles everything automatically.

## Troubleshooting

### "functions-framework: command not found"

**If using venv method:**
```bash
# Make sure venv is activated
source .venv/bin/activate

# Reinstall
pip install functions-framework
```

**If using uv method:**
```bash
# Install dependencies
uv pip install functions-framework pydantic flask
```

### Port already in use

```bash
# Find what's using port 8081
lsof -i :8081

# Kill it
kill -9 <PID>

# Or use a different port
uv run functions-framework --target=thermostat_handler --port=9000
```

### Module not found errors

```bash
# Make sure you're in the dummy_nest_api directory
cd dummy_nest_api

# Reinstall dependencies
uv pip install functions-framework pydantic flask
```

## Deployment to GCP

Deploy to the `jsb-genai-sa` GCP project:

```bash
./deploy.sh
```

This will:
- Deploy as a Gen2 Cloud Function
- Region: us-central1
- Runtime: Python 3.11
- Allow unauthenticated access
- Memory: 256Mi

## Mock Data

The API returns mock data for 3 thermostats:
- **thermostat-1**: Living Room (cooling mode, 72°F current, 70°F target)
- **thermostat-2**: Bedroom (heating mode, 68°F current, 68°F target)
- **thermostat-3**: Office (off mode, 74°F current, 72°F target)

All data is stateless and resets on each request.

## Summary

**Quick Start:**
- **Best for beginners:** `./run_with_uv.sh`
- **Best for uv users:** `uv run functions-framework --target=thermostat_handler --port=8081 --debug`
- **Best for traditional Python:** `./run_local.sh`

All methods work equally well - choose what you prefer!
