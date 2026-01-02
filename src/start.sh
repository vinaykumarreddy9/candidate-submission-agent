#!/bin/bash

# Start FastAPI backend in the background on an internal port
# Using src.backend.main:app ensures it can be found from the project root
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
sleep 5

# Start Streamlit frontend on the port assigned by Render ($PORT)
streamlit run src/frontend/app.py --server.port $PORT --server.address 0.0.0.0
