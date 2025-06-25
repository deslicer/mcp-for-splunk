#!/bin/bash

# Build and run MCP Server for Splunk
# This script builds the Docker image and runs it with the docker-compose setup

set -e  # Exit on error

# Change to the project root directory (parent of scripts)
cd "$(dirname "$0")/.."

echo "🚀 Building and Running MCP Server for Splunk"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose not found. Please install docker-compose."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from env.example..."
    cp env.example .env
    print_warning "Please edit .env file with your configuration before running again."
    exit 0
fi

print_status "Building Docker image..."
docker-compose build mcp-server

if [ $? -eq 0 ]; then
    print_success "Docker image built successfully!"
else
    print_error "Failed to build Docker image"
    exit 1
fi

print_status "Starting services with docker-compose..."
docker-compose up -d

if [ $? -eq 0 ]; then
    print_success "Services started successfully!"
else
    print_error "Failed to start services"
    exit 1
fi

# Wait a moment for services to start
sleep 5

print_status "Checking service status..."
docker-compose ps

print_status "Checking MCP server logs..."
docker-compose logs mcp-server --tail=20

echo
print_success "🎉 Setup complete!"
echo
echo "📋 Service URLs:"
echo "   🔧 Traefik Dashboard: http://localhost:8080"
echo "   🌐 Splunk Web UI:     http://localhost:9000"
echo "   🔌 MCP Server:        http://localhost:8001"
echo "   📊 MCP Inspector:     http://localhost:6274"
echo
echo "🔍 To check logs:"
echo "   docker-compose logs -f mcp-server"
echo
echo "🛑 To stop all services:"
echo "   docker-compose down" 