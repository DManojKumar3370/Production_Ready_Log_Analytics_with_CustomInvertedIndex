#!/bin/bash

echo "Setting up Log Analytics Pipeline..."

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✓ .env created"
else
    echo "✓ .env already exists"
fi

echo "Creating data directories..."
mkdir -p data/docs data/index reports
echo "✓ Data directories created"

echo ""
echo "Building Docker images..."
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to become healthy..."
sleep 15

echo ""
echo "Checking service status..."
docker-compose ps

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Monitor logs: docker-compose logs -f"
echo "2. Query logs: docker-compose run --rm querier search 'error'"
echo "3. View aggregations: docker-compose run --rm querier aggregate count --by service,level --last 1h"
echo "4. Run benchmark: ./benchmark.sh"
