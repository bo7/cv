#!/bin/bash

# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    libpango1.0-dev

# Create application directory
sudo mkdir -p /var/www/cvflask
sudo chown $USER:$USER /var/www/cvflask
cd /var/www/cvflask

# Clone repository
git clone https://github.com/bo7/cv.git .

# Setup Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file (manually add sensitive values later)
cat > .env << EOL
FLASK_SECRET_KEY=$(openssl rand -hex 32)
ANTHROPIC_API_KEY=your_api_key_here
LOGIN_PASSWORD=your_password_here
EOL

# Set proper permissions for .env
chmod 600 .env

echo "Environment file created with secure permissions. Please update the .env file with your actual credentials." 