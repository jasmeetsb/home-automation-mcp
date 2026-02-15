#!/bin/bash

# Dummy NEST API Deployment Script
# Deploys the Cloud Function to GCP project jsb-genai-sa

set -e

# Configuration
PROJECT_ID="jsb-genai-sa"
FUNCTION_NAME="dummy-nest-api"
REGION="us-central1"
RUNTIME="python311"
ENTRY_POINT="thermostat_handler"
MEMORY="256Mi"
TIMEOUT="60s"

echo "=================================="
echo "Deploying Dummy NEST API"
echo "=================================="
echo "Project: $PROJECT_ID"
echo "Function: $FUNCTION_NAME"
echo "Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "Error: Not logged in to gcloud"
    echo "Run: gcloud auth login"
    exit 1
fi

# Set project
echo "Setting project to $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Deploy function
echo ""
echo "Deploying function..."
gcloud functions deploy "$FUNCTION_NAME" \
    --gen2 \
    --runtime="$RUNTIME" \
    --region="$REGION" \
    --source=. \
    --entry-point="$ENTRY_POINT" \
    --trigger-http \
    --allow-unauthenticated \
    --memory="$MEMORY" \
    --timeout="$TIMEOUT" \
    --max-instances=10

# Get the function URL
echo ""
echo "Getting function URL..."
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
    --region="$REGION" \
    --gen2 \
    --format="value(serviceConfig.uri)")

echo ""
echo "=================================="
echo "Deployment Complete!"
echo "=================================="
echo "Function URL: $FUNCTION_URL"
echo ""
echo "Test endpoints:"
echo "  GET  $FUNCTION_URL/thermostats"
echo "  GET  $FUNCTION_URL/thermostats/thermostat-1"
echo "  POST $FUNCTION_URL/thermostats/thermostat-1/temperature"
echo "  GET  $FUNCTION_URL/thermostats/thermostat-1/history"
echo ""
echo "Example curl command:"
echo "curl $FUNCTION_URL/thermostats"
echo ""
