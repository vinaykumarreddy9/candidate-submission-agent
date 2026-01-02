#!/bin/bash

# Start FastAPI backend in the background on an internal port
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
sleep 5

# Start Streamlit frontend on the port assigned by Render ($PORT)
# This ensures that hitting the Render URL displays the Streamlit UI
streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0
