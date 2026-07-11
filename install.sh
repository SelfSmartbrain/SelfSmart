#!/bin/bash
# ModelX Voice Assistant - Installation Script

set -e

# Parse arguments
CREATE_DESKTOP=false
for arg in "$@"; do
    case $arg in
        --desktop)
            CREATE_DESKTOP=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./install.sh [--desktop]"
            echo "  --desktop    Create desktop entry (Linux only)"
            exit 0
            ;;
    esac
done

echo "🎤 Installing ModelX Voice Assistant..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

echo -e "${YELLOW}Detected OS: $OS ($ARCH)${NC}"

# Install system dependencies
install_system_deps() {
    if [[ "$OS" == "Darwin" ]]; then
        echo -e "${YELLOW}Installing macOS dependencies...${NC}"
        if command -v brew &> /dev/null; then
            brew install portaudio ffmpeg
        else
            echo -e "${RED}Homebrew not found. Please install from https://brew.sh${NC}"
            exit 1
        fi
    elif [[ "$OS" == "Linux" ]]; then
        echo -e "${YELLOW}Installing Linux dependencies...${NC}"
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y portaudio19-dev ffmpeg python3-dev
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y portaudio-devel ffmpeg python3-devel
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm portaudio ffmpeg python
        else
            echo -e "${RED}Unsupported package manager. Please install portaudio and ffmpeg manually.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Unknown OS. Please install portaudio and ffmpeg manually.${NC}"
    fi
}

# Check Python version
check_python() {
    echo -e "${YELLOW}Checking Python version...${NC}"
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    REQUIRED_VERSION="3.10"
    
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
        echo -e "${GREEN}Python $PYTHON_VERSION ✓${NC}"
    else
        echo -e "${RED}Python 3.10+ required. Found $PYTHON_VERSION${NC}"
        exit 1
    fi
}

# Install Python package
install_python_package() {
    echo -e "${YELLOW}Installing Python package...${NC}"
    pip install --upgrade pip
    pip install -e .
}

# Download voice models
download_voices() {
    echo -e "${YELLOW}Downloading voice models...${NC}"
    python3 -c "
from modelx_voice.tts import VoiceManager
import asyncio
vm = VoiceManager()
voices = vm.list_available_voices()
print('Available voices:', voices)
" 2>/dev/null || echo "Voice models will be downloaded on first run"
}

# Create desktop entry (Linux) - optional
create_desktop_entry() {
    if [[ "$CREATE_DESKTOP" == true ]] && [[ "$OS" == "Linux" ]] && [[ -d "$HOME/.local/share/applications" ]]; then
        cat > "$HOME/.local/share/applications/modelx.desktop" << EOF
[Desktop Entry]
Name=ModelX
Comment=AI Assistant Platform
Exec=modelx voice
Terminal=true
Type=Application
Categories=Utility;
EOF
        echo -e "${GREEN}Desktop entry created${NC}"
    fi
}

# Main installation flow
main() {
    check_python
    install_system_deps
    install_python_package
    download_voices
    create_desktop_entry
    
    echo ""
    echo -e "${GREEN}✓ Installation complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run: modelx --setup"
    echo "  2. Enter your API key when prompted"
    echo "  3. Start talking!"
    echo ""
    echo "Commands:"
    echo "  modelx              Start voice assistant"
    echo "  modelx voice        Start voice assistant (explicit)"
    echo "  modelx --setup      Run setup wizard"
    echo "  modelx doctor       System diagnostics"
    echo "  modelx self-test    Run self-tests"
    echo "  modelx --help       Show all options"
    if [[ "$CREATE_DESKTOP" != true ]] && [[ "$OS" == "Linux" ]]; then
        echo ""
        echo "Tip: Run './install.sh --desktop' to create a desktop launcher"
    fi
}

main "$@"