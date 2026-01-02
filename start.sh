#!/bin/bash

# Start FastAPI backend in the background
uvicorn backend.main:app --host 0.0.0.0 --port $PORT &

# Wait for backend to be ready
sleep 5

# Start Streamlit frontend
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
