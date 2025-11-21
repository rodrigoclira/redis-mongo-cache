#!/bin/bash

# Quick Start Script for L1 Cache Demo
# This script sets up and runs the entire project

set -e  # Exit on error

echo "=========================================="
echo "L1 Cache Strategy Demo - Quick Start"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Docker and Docker Compose are installed"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_warning "Creating .env file from .env.example..."
    cp .env.example .env
    print_success ".env file created"
else
    print_success ".env file already exists"
fi

# Stop any running containers
echo ""
echo "Stopping any running containers..."
docker compose down 2>/dev/null || true

# Start services
echo ""
echo "Starting services (Redis, MongoDB, Django)..."
docker compose up -d

# Wait for services to be healthy
echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check if services are running
if docker compose ps | grep -q "Up"; then
    print_success "Services are running"
else
    print_error "Services failed to start"
    docker-compose logs
    exit 1
fi

# Run migrations
echo ""
echo "Running Django migrations..."
docker compose exec -T web python manage.py migrate

# Create sample data
echo ""
echo "Creating sample data..."
docker compose exec -T web python manage.py populate_sample_data --count 10

# Display service status
echo ""
echo "=========================================="
echo "Services Status:"
echo "=========================================="
docker compose ps

# Display URLs
echo ""
echo "=========================================="
echo "🎉 Setup Complete!"
echo "=========================================="
echo ""
echo "Available URLs:"
echo "  • API Base:         http://localhost:8000/api/"
echo "  • Swagger UI:       http://localhost:8000/swagger/"
echo "  • ReDoc:            http://localhost:8000/redoc/"
echo "  • Health Check:     http://localhost:8000/api/health/"
echo "  • Cache Info:       http://localhost:8000/api/info/"
echo ""
echo "Quick Test Commands:"
echo "  # Test health check"
echo "  curl http://localhost:8000/api/health/ | jq"
echo ""
echo "  # Get sample customer data"
echo "  curl http://localhost:8000/api/features/CUST00001/ | jq"
echo ""
echo "  # View logs"
echo "  docker-compose logs -f web"
echo ""
echo "For detailed testing guide, see TESTING.md"
echo ""
print_success "Ready to demonstrate L1 cache strategy!"
