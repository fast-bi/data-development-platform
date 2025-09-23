#!/bin/bash

# Define your project directory
PROJECT_DIR=".fasbicustomertenant"

# Create a virtual environment in your project directory
python3 -m venv $PROJECT_DIR/venv

# Activate the virtual environment
source $PROJECT_DIR/venv/bin/activate

# Upgrade pip to its latest version
python -m pip install --upgrade pip

# Install required Python packages from requirements.txt
python -m pip install -r requirements.txt

# Output the installed packages for verification
python -m pip freeze

echo "Setup completed. Virtual environment is ready to use."

