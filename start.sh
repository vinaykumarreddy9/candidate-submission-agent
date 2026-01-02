#!/bin/bash

# Start FastAPI backend in the background
echo "🚀 Starting FastAPI Backend..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
echo "⏳ Waiting for backend..."
sleep 5

# Start Streamlit frontend
echo "🎨 Starting Streamlit Frontend on Port $PORT..."
streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
