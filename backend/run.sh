#!/bin/bash

# Lane RFP Agent Backend Startup Script

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run FastAPI server
echo "Starting FastAPI server..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
