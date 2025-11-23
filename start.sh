#!/bin/bash

# Quick Start Script for FileForge

echo "🚀 Starting FileForge Platform..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created (you can edit it to add GEMINI_API_KEY)"
    echo ""
fi

# Build and start services
echo "🏗️  Building and starting services..."
echo "This may take a few minutes on first run..."
echo ""

docker-compose up -d --build

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✨ FileForge is now running!"
echo ""
echo "📍 Access Points:"
echo "   • API Documentation: http://localhost/docs"
echo "   • Backend API: http://localhost/api"
echo "   • MinIO Console: http://localhost:9001 (minio/minio123)"
echo "   • RabbitMQ Management: http://localhost:15672 (guest/guest)"
echo ""
echo "📖 Quick Commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart: docker-compose restart"
echo ""
echo "🎯 Ready to use! Check the API docs at http://localhost/docs"
