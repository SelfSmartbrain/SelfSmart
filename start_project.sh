#!/usr/bin/env bash

# SelfSmart AI - Complete Project Startup Script
# This script starts all services: databases, backend, and frontend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
ROOT="$(cd "$(dirname "$0")" && pwd)"
USE_DOCKER=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-docker) USE_DOCKER=false; shift ;;
        --backend-port) BACKEND_PORT="$2"; shift 2 ;;
        --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# Print banner
print_banner() {
    echo -e "${BLUE}"
    cat <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║              SelfSmart AI - Complete Startup                ║
║                                                              ║
║  �️  PostgreSQL + Qdrant + Redis + Neo4j                    ║
║  🚀 FastAPI Backend + Next.js Frontend                       ║
║  🤖 Autonomous Agent Platform                                ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Check if command exists
check_cmd() {
    command -v "$1" >/dev/null 2>&1
}

# Check environment file
check_env() {
    log "Checking environment configuration..."
    if [[ ! -f "$ROOT/.env" ]]; then
        warn "No .env file found. Copying from .env.example..."
        cp "$ROOT/.env.example" "$ROOT/.env"
        error "Please edit .env with your API keys and configuration, then re-run"
    fi
    success "Environment file exists"
}

# Start Docker services
start_docker_services() {
    if [[ "$USE_DOCKER" == true ]] && check_cmd docker; then
        log "Starting Docker services (PostgreSQL, Qdrant, Redis, Neo4j)..."
        cd "$ROOT"
        docker-compose up -d postgres qdrant redis neo4j 2>/dev/null || \
            warn "Docker services failed to start, assuming they're running externally"
        
        # Wait for services to be ready
        log "Waiting for databases to be ready..."
        sleep 5
    else
        warn "Docker not available or disabled. Ensure PostgreSQL, Qdrant, Redis, Neo4j are running manually"
    fi
}

# Setup Backend
setup_backend() {
    log "Setting up Backend..."
    cd "$ROOT"
    
    if [ ! -d ".venv" ]; then
        log "Creating virtual environment..."
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    log "Installing/Updating backend dependencies..."
    pip install -e ".[dev]" --quiet
    
    # Run database migrations
    log "Running database migrations..."
    alembic upgrade head || warn "Migrations failed (database may not be ready yet)"
    
    success "Backend setup complete"
}

# Setup Frontend
setup_frontend() {
    log "Setting up Frontend..."
    cd "$ROOT/frontend"
    
    if [ ! -d "node_modules" ]; then
        log "Installing frontend dependencies (this may take a minute)..."
        npm install --silent
    fi
    
    success "Frontend setup complete"
}

# Create logs directory
setup_logs() {
    mkdir -p "$ROOT/logs"
}

# Start Backend
start_backend() {
    log "Starting FastAPI Backend on http://localhost:$BACKEND_PORT..."
    cd "$ROOT"
    export PYTHONPATH="$ROOT"
    
    python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port "$BACKEND_PORT" > "$ROOT/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$ROOT/backend_pid.txt"
    
    # Wait for backend to start
    sleep 3
    if kill -0 $BACKEND_PID 2>/dev/null; then
        success "Backend started (PID: $BACKEND_PID)"
    else
        error "Backend failed to start. Check logs/backend.log"
    fi
}

# Start Frontend
start_frontend() {
    log "Starting Next.js Frontend on http://localhost:$FRONTEND_PORT..."
    cd "$ROOT/frontend"
    
    npm run dev > "$ROOT/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$ROOT/frontend_pid.txt"
    
    # Wait for frontend to start
    sleep 5
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        success "Frontend started (PID: $FRONTEND_PID)"
    else
        error "Frontend failed to start. Check logs/frontend.log"
    fi
}

# Cleanup function
cleanup() {
    log "Stopping services..."
    
    # Kill backend
    if [ -f "$ROOT/backend_pid.txt" ]; then
        BACKEND_PID=$(cat "$ROOT/backend_pid.txt")
        kill $BACKEND_PID 2>/dev/null || true
        rm "$ROOT/backend_pid.txt"
    fi
    
    # Kill frontend
    if [ -f "$ROOT/frontend_pid.txt" ]; then
        FRONTEND_PID=$(cat "$ROOT/frontend_pid.txt")
        kill $FRONTEND_PID 2>/dev/null || true
        rm "$ROOT/frontend_pid.txt"
    fi
    
    # Optionally stop Docker services
    if [[ "$USE_DOCKER" == true ]] && check_cmd docker; then
        read -p "Stop Docker services? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$ROOT"
            docker-compose down
        fi
    fi
    
    success "All services stopped"
    exit
}

# Main execution
main() {
    print_banner
    
    check_env
    start_docker_services
    setup_logs
    setup_backend
    setup_frontend
    
    log "Starting all services..."
    start_backend
    start_frontend
    
    echo ""
    success "🎉 SelfSmart AI is now running!"
    echo ""
    echo -e "${GREEN}▶ Backend:  http://localhost:$BACKEND_PORT${NC}"
    echo -e "${GREEN}▶ Frontend: http://localhost:$FRONTEND_PORT${NC}"
    echo -e "${GREEN}▶ API Docs: http://localhost:$BACKEND_PORT/docs${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
    echo ""
    
    # Trap signals for cleanup
    trap cleanup SIGINT SIGTERM
    
    # Keep script running
    while true; do
        sleep 1
        # Check if processes are still running
        if [ -f "$ROOT/backend_pid.txt" ]; then
            BACKEND_PID=$(cat "$ROOT/backend_pid.txt")
            if ! kill -0 $BACKEND_PID 2>/dev/null; then
                error "Backend process died unexpectedly"
            fi
        fi
        if [ -f "$ROOT/frontend_pid.txt" ]; then
            FRONTEND_PID=$(cat "$ROOT/frontend_pid.txt")
            if ! kill -0 $FRONTEND_PID 2>/dev/null; then
                error "Frontend process died unexpectedly"
            fi
        fi
    done
}

main "$@"
