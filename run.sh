#!/usr/bin/env bash
# ModelX Voice Assistant - One-Command Build & Run
# Usage: ./run.sh [--dev] [--skip-deps] [--skip-models] [--port PORT]

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$PROJECT_ROOT/src/voice_assistant/models"
PIPER_DIR="$MODELS_DIR/piper"
VENV_DIR="$PROJECT_ROOT/.venv"
PORT=8000
DEV_MODE=false
SKIP_DEPS=false
SKIP_MODELS=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev) DEV_MODE=true; shift ;;
        --skip-deps) SKIP_DEPS=true; shift ;;
        --skip-models) SKIP_MODELS=true; shift ;;
        --port) PORT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    else
        OS="unknown"
    fi
    log "Detected OS: $OS"
}

# Check command exists
check_cmd() {
    command -v "$1" >/dev/null 2>&1
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    if [[ "$OS" == "macos" ]]; then
        if ! check_cmd brew; then
            error "Homebrew required. Install from https://brew.sh"
        fi
        # Use system Python (already installed), just need ffmpeg + portaudio
        brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
        brew list portaudio >/dev/null 2>&1 || brew install portaudio
    elif [[ "$OS" == "linux" ]]; then
        if check_cmd apt-get; then
            sudo apt-get update && sudo apt-get install -y \
                python3 python3-venv python3-dev \
                ffmpeg libportaudio2 portaudio19-dev \
                build-essential curl wget git
        elif check_cmd dnf; then
            sudo dnf install -y python3 python3-devel \
                ffmpeg portaudio-devel gcc gcc-c++ make curl wget git
        elif check_cmd pacman; then
            sudo pacman -S --needed python ffmpeg portaudio base-devel curl wget git
        else
            warn "Unknown package manager. Install manually: python3, ffmpeg, portaudio"
        fi
    fi
}

# Setup Python virtual environment
setup_venv() {
    log "Setting up Python virtual environment..."
    if [[ ! -d "$VENV_DIR" ]]; then
        # Use system Python with --without-pip workaround for ensurepip issues
        local python_bin="python3"
        log "Using Python: $($python_bin --version)"
        "$python_bin" -m venv "$VENV_DIR" --without-pip
        # Install pip manually
        curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV_DIR/bin/python"
    fi
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip setuptools wheel
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    source "$VENV_DIR/bin/activate"
    
    # Core deps
    pip install -q \
        fastapi==0.109.0 \
        uvicorn[standard]==0.27.0 \
        websockets==12.0 \
        pyaudio==0.2.14 \
        sounddevice==0.4.6 \
        numpy==1.26.0 \
        openai-whisper==20231117 \
        torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu \
        langchain==0.1.0 \
        langchain-core==0.1.0 \
        langchain-anthropic==0.1.0 \
        langchain-openai==0.1.0 \
        neo4j==5.18.0 \
        redis==5.0.0 \
        qdrant-client==1.8.0 \
        psycopg2-binary==2.9.9 \
        sqlalchemy==2.0.25 \
        pydantic==2.5.0 \
        pydantic-settings==2.1.0

    # Optional: edge-tts for cloud TTS fallback
    pip install -q edge-tts==6.1.0 || warn "edge-tts install failed (optional)"
}

# Install Piper TTS binary
install_piper() {
    log "Installing Piper TTS..."
    if check_cmd piper; then
        success "Piper already installed"
        return
    fi

    if [[ "$OS" == "macos" ]]; then
        brew install piper
    elif [[ "$OS" == "linux" ]]; then
        # Download prebuilt binary
        local arch=$(uname -m)
        local piper_url="https://github.com/rhasspy/piper/releases/latest/download/piper_${arch}.tar.gz"
        log "Downloading Piper from $piper_url"
        cd /tmp
        wget -q "$piper_url" -O piper.tar.gz
        tar -xzf piper.tar.gz
        sudo mv piper/piper /usr/local/bin/
        sudo mv piper/libpiper_phonemize.so /usr/local/lib/ 2>/dev/null || true
        ldconfig 2>/dev/null || true
        cd "$PROJECT_ROOT"
    fi
}

# Install whisper.cpp
install_whisper_cpp() {
    log "Installing whisper.cpp..."
    if check_cmd whisper-cpp || [[ -f "/usr/local/bin/whisper-cpp" ]]; then
        success "whisper.cpp already installed"
        return
    fi

    if [[ "$OS" == "macos" ]]; then
        brew install whisper-cpp
    elif [[ "$OS" == "linux" ]]; then
        cd /tmp
        git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git
        cd whisper.cpp
        make -j$(nproc)
        sudo cp main /usr/local/bin/whisper-cpp
        cd "$PROJECT_ROOT"
    fi
}

# Download models
download_models() {
    log "Downloading models..."
    mkdir -p "$MODELS_DIR" "$PIPER_DIR"

    # Whisper model
    local whisper_model="$MODELS_DIR/ggml-base.en.bin"
    if [[ ! -f "$whisper_model" ]]; then
        log "Downloading Whisper base.en model (142 MB)..."
        wget -q --show-progress \
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" \
            -O "$whisper_model"
    else
        success "Whisper model exists"
    fi

    # Piper voice - lessac medium (female, natural)
    local piper_model="$PIPER_DIR/en_US-lessac-medium.onnx"
    local piper_config="$PIPER_DIR/en_US-lessac-medium.onnx.json"
    
    if [[ ! -f "$piper_model" ]]; then
        log "Downloading Piper voice: en_US-lessac-medium (54 MB)..."
        wget -q --show-progress \
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" \
            -O "$piper_model"
    else
        success "Piper model exists"
    fi

    if [[ ! -f "$piper_config" ]]; then
        wget -q \
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" \
            -O "$piper_config"
    fi

    # Alternative voices (optional)
    for voice in "en_US-amy-low" "en_US-libritts-medium"; do
        local vmodel="$PIPER_DIR/${voice}.onnx"
        local vconfig="$PIPER_DIR/${voice}.onnx.json"
        if [[ ! -f "$vmodel" ]]; then
            log "Downloading optional voice: $voice..."
            wget -q --show-progress \
                "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/${voice/-/\/}/${voice}.onnx" \
                -O "$vmodel" 2>/dev/null || warn "Could not download $voice"
            wget -q \
                "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/${voice/-/\/}/${voice}.onnx.json" \
                -O "$vconfig" 2>/dev/null || true
        fi
    done
}

# Check environment file
check_env() {
    log "Checking environment configuration..."
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        warn "No .env file found. Creating template..."
        cat > "$PROJECT_ROOT/.env" <<'EOF'
# ModelX Voice Assistant Configuration
# Required: Anthropic API Key for LLM
ANTHROPIC_API_KEY=your_anthropic_key_here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Optional: OpenAI for embeddings
OPENAI_API_KEY=your_openai_key_here
EMBEDDING_MODEL=text-embedding-3-large

# Database (PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=agent_platform
POSTGRES_USER=agent
POSTGRES_PASSWORD=agent_password

# Vector DB (Qdrant)
QDRANT_URL=http://localhost:6333

# Graph DB (Neo4j)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j_password

# Cache (Redis)
REDIS_URL=redis://localhost:6379/0

# MCP Servers (optional)
# MCP_SERVERS=[{"name":"filesystem","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/workspace"]}]
EOF
        error "Please edit .env with your API keys, then re-run"
    fi
    success "Environment file exists"
}

# Start databases (Docker)
start_databases() {
    log "Starting databases..."
    if check_cmd docker; then
        cd "$PROJECT_ROOT"
        if [[ -f "docker-compose.yml" ]]; then
            docker-compose up -d postgres qdrant neo4j redis 2>/dev/null || \
                warn "docker-compose failed, assuming databases running externally"
        else
            warn "No docker-compose.yml, skipping database startup"
        fi
    else
        warn "Docker not found. Ensure PostgreSQL, Qdrant, Neo4j, Redis are running"
    fi
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    source "$VENV_DIR/bin/activate"
    cd "$PROJECT_ROOT"
    python -c "
from src.config.settings import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from src.memory.episodic_memory import Base
import asyncio

async def migrate():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print('Migrations complete')

asyncio.run(migrate())
" || warn "Migrations failed (DB may not be ready)"
}

# Main run function
run_server() {
    log "Starting Voice Assistant on port $PORT..."
    source "$VENV_DIR/bin/activate"
    cd "$PROJECT_ROOT"
    
    export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
    
    if [[ "$DEV_MODE" == true ]]; then
        exec python -m uvicorn src.voice_assistant.server:app \
            --host 0.0.0.0 --port "$PORT" --reload
    else
        exec python -m uvicorn src.voice_assistant.server:app \
            --host 0.0.0.0 --port "$PORT"
    fi
}

# Print banner
print_banner() {
    echo -e "${BLUE}"
    cat <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║         ModelX Voice Assistant - One-Command Runner         ║
║                                                              ║
║  🎤 Whisper STT (local)    🧠 ModelX Cognitive Brain        ║
║  🔊 Piper TTS (female)     🤖 Planning, Agents, Tools       ║
║  🌐 Web UI + WebSocket     💾 Memory + Self-Improvement     ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Main
main() {
    print_banner
    detect_os

    if [[ "$SKIP_DEPS" != true ]]; then
        install_system_deps
        setup_venv
        install_python_deps
        install_piper
        install_whisper_cpp
    else
        log "Skipping dependency installation"
        source "$VENV_DIR/bin/activate" 2>/dev/null || error "Venv not found. Run without --skip-deps first"
    fi

    if [[ "$SKIP_MODELS" != true ]]; then
        download_models
    else
        log "Skipping model downloads"
    fi

    check_env
    start_databases
    run_migrations

    success "Setup complete! Starting server..."
    echo ""
    echo -e "${GREEN}▶ Open http://localhost:$PORT in your browser${NC}"
    echo -e "${GREEN}▶ Press Ctrl+C to stop${NC}"
    echo ""

    run_server
}

# Trap cleanup
cleanup() {
    log "Shutting down..."
    exit 0
}
trap cleanup INT TERM

main "$@"