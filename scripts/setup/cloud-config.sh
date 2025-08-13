#!/bin/bash
# Google Cloud VM setup script

echo "🚀 Setting up Trading System on Google Cloud"

# Update system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Docker
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p ~/trading-system
cd ~/trading-system

# Clone or copy your code here
# (You'll upload the files separately)

echo "✅ VM setup complete"
echo "Next: Upload your trading system files"
