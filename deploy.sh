#!/bin/bash

# Define paths
APP_PATH=/var/www/cvflask
VENV_PATH=$APP_PATH/venv

# Pull latest changes
cd $APP_PATH
git pull

# Activate virtual environment and install dependencies
source $VENV_PATH/bin/activate
pip install -r requirements.txt

# Copy service file if it doesn't exist
if [ ! -f /etc/systemd/system/cvflask.service ]; then
    sudo cp cvflask.service /etc/systemd/system/
    sudo systemctl daemon-reload
fi

# Restart the service
sudo systemctl restart cvflask

# Show status
sudo systemctl status cvflask 