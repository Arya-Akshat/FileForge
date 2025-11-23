#!/bin/bash

# Development setup script

echo "🔧 Setting up development environment..."
echo ""

# Backend setup
echo "📦 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Backend setup complete"
echo ""

# Create .env if needed
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created backend/.env"
fi

cd ..

echo ""
echo "✨ Development environment ready!"
echo ""
echo "📍 To start development:"
echo "   1. Start infrastructure: docker-compose up -d db minio rabbitmq"
echo "   2. Activate venv: cd backend && source venv/bin/activate"
echo "   3. Run migrations: alembic upgrade head"
echo "   4. Start backend: uvicorn app.main:app --reload"
echo "   5. Visit: http://localhost:8000/docs"
