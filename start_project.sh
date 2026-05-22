#!/usr/bin/env bash

# SmartSelf AI - Unified Start Script
# This script builds and starts both the FastAPI backend and Next.js frontend.

set -e

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Starting SmartSelf AI Project..."

# 1. Setup Backend
echo "📦 Setting up Backend..."
cd "$ROOT"
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing/Updating backend dependencies..."
pip install -r requirements.txt --quiet

# 2. Setup Frontend
echo "⚛️ Setting up Frontend..."
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (this may take a minute)..."
    npm install --silent
fi

# 3. Start Services
echo "🔥 Starting services..."

# Start Backend in background
echo "Starting FastAPI Backend on http://localhost:$BACKEND_PORT..."
cd "$ROOT"
export PYTHONPATH="$ROOT"
# Using the specialized python3 path from run_server.sh to ensure compatibility
/usr/bin/python3 -m src.web_server > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Function to kill background process on exit
cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID
    exit
}
trap cleanup SIGINT SIGTERM

# Start Frontend
echo "Starting Next.js Frontend on http://localhost:$FRONTEND_PORT..."
cd "$ROOT/frontend"
npm run dev
