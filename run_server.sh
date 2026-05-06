#!/bin/bash
# Automatically activate the virtual environment and start the backend server

if [ ! -d "venv" ]; then
    echo "Virtual environment not found! Please run 'python3 -m venv venv' and install requirements first."
    exit 1
fi

source venv/bin/activate
echo "Starting Termi-Chat Backend Server..."
echo "Web Client will be available at: http://127.0.0.1:8000"
uvicorn server.main:app --host 127.0.0.1 --port 8000
