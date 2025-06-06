#!/bin/bash

set -e

echo "=== Starting deployment ==="

if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up the repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

if ! groups $USER | grep -q '\bdocker\b'; then
    echo "Adding user to docker group..."
    sudo usermod -aG docker $USER
    newgrp docker
fi

echo "Creating directories..."
mkdir -p static/uploads database
chmod 755 static/uploads database

echo "Cleaning up old containers..."
docker-compose down --remove-orphans || true

echo "Building containers..."
for i in {1..3}; do
    if docker-compose build; then
        break
    fi
    echo "Build attempt $i failed, retrying..."
    sleep 5
done

echo "Starting services..."
docker-compose up -d

echo "Checking container status..."
if ! docker-compose ps | grep -q "Up"; then
    echo "Error: Containers failed to start"
    docker-compose logs
    exit 1
fi

echo ""
echo "=== Deployment successful! ==="
echo "Application running at: http://localhost:5000"
echo ""
echo "Management commands:"
echo "  Stop: docker-compose down"
echo "  Logs: docker-compose logs -f"
echo "  Shell: docker-compose exec web bash"
echo "=============================="