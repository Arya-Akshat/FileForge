#!/bin/bash

# View logs for all services or specific service

if [ -z "$1" ]; then
    echo "📋 Viewing logs for all services..."
    echo "   Press Ctrl+C to exit"
    echo ""
    docker-compose logs -f --tail=100
else
    echo "📋 Viewing logs for $1..."
    echo "   Press Ctrl+C to exit"
    echo ""
    docker-compose logs -f --tail=100 "$1"
fi
