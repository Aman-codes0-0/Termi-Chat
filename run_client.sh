#!/bin/bash
# Automatically activate the virtual environment and start the Textual client

if [ ! -d "venv" ]; then
    echo "Virtual environment not found! Please run 'python3 -m venv venv' and install requirements first."
    exit 1
fi

source venv/bin/activate
echo "Starting Termi-Chat Client..."
python client/app.py
