#!/usr/bin/env python3
"""
ModelX Voice Assistant - Cross-Platform Build & Run
Usage: python run.py [--dev] [--skip-deps] [--skip-models] [--port PORT]
"""

import argparse
import asyncio
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# Config
ROOT = Path(__file__).parent
MODELS_DIR = ROOT / "src" / "voice_assistant" / "models"
PIPER_DIR = MODELS_DIR / "piper"
VENV_DIR = ROOT / ".venv"
PORT = 8000

OS_NAME = platform.system().lower()

# Colors
class C:
    R = '\033[0;31m'
    G = '\033[0;32m'
    Y = '\033[1;33m'
    B = '\033[0;34m'
    X = '\033[0m'

def log(msg): print(f"{C.B}[INFO]{C.X} {msg}")
def ok(msg): print(f"{C.G}[OK]{C.X} {msg}")
def warn(msg): print(f"{C.Y}[WARN]{C.X} {msg}")
def err(msg): print(f"{C.R}[ERROR]{C.X} {msg}"); sys.exit(1)

def run_cmd(cmd, check=True, **kw):
    log(f"$ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    return subprocess.run(cmd, check=check, **kw)

def has_cmd(cmd):
    return shutil.which(cmd) is not None

def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        ok(f"Exists: {dest.name}")
        return
    log(f"Downloading {dest.name}...")
    try:
        def progress(b, bs, ts):
            if ts > 0:
                pct = min(100, b * bs * 100 // ts)
                sys.stdout.write(f"\r  {pct}%")
                sys.stdout.flush()
        urllib.request.urlretrieve(url, dest, reporthook=progress)
        print()
        ok(f"Downloaded: {dest.name}")
    except Exception as e:
        err(f"Download failed: {e}")

def install_system():
    log("Installing system dependencies...")
    if OS_NAME == "darwin":
        if not has_cmd("brew"): err("Homebrew required")
        for pkg in ["python@3.11", "ffmpeg", "portaudio"]:
            run_cmd(["brew", "list", pkg], check=False) or run_cmd(["brew", "install", pkg])
    elif OS_NAME == "linux":
        if has_cmd("apt-get"):
            run_cmd(["sudo", "apt-get", "update"])
            run_cmd(["sudo", "apt-get", "install", "-y",
                "python3.11", "python3.11-venv", "python3.11-dev",
                "ffmpeg", "libportaudio2", "portaudio19-dev",
                "build-essential", "curl", "wget", "git"])
        elif has_cmd("dnf"):
            run_cmd(["sudo", "dnf", "install", "-y",
                "python3.11", "python3.11-devel", "ffmpeg",
                "portaudio-devel", "gcc", "gcc-c++", "make", "curl", "wget", "git"])
        elif has_cmd("pacman"):
            run_cmd(["sudo", "pacman", "-S", "--needed",
                "python", "ffmpeg", "portaudio", "base-devel", "curl", "wget", "git"])
        else:
            warn("Install manually: python3.11, ffmpeg, portaudio")

def setup_venv():
    log("Setting up virtual environment...")
    if not VENV_DIR.exists():
        run_cmd([sys.executable, "-m", "venv", str(VENV_DIR)])
    pip = VENV_DIR / "bin" / "pip"
    run_cmd([str(pip), "install", "-q", "--upgrade", "pip", "setuptools", "wheel"])

def install_python_deps():
    log("Installing Python packages...")
    pip = VENV_DIR / "bin" / "pip"
    # Install from pyproject.toml to avoid version conflicts
    run_cmd([str(pip), "install", "-q", "-e", "."], cwd=ROOT)

def install_piper():
    log("Installing Piper TTS...")
    if has_cmd("piper"): return ok("Piper exists")
    if OS_NAME == "darwin":
        run_cmd(["brew", "install", "piper"])
    else:
        arch = platform.machine()
        url = f"https://github.com/rhasspy/piper/releases/latest/download/piper_{arch}.tar.gz"
        run_cmd(["wget", "-q", url, "-O", "/tmp/piper.tar.gz"])
        run_cmd(["tar", "-xzf", "/tmp/piper.tar.gz", "-C", "/tmp"])
        run_cmd(["sudo", "mv", "/tmp/piper/piper", "/usr/local/bin/"])
        run_cmd(["sudo", "mv", "/tmp/piper/libpiper_phonemize.so", "/usr/local/lib/"], check=False)
        run_cmd(["sudo", "ldconfig"], check=False)

def install_whisper_cpp():
    log("Installing whisper.cpp...")
    if has_cmd("whisper-cpp") or Path("/usr/local/bin/whisper-cpp").exists():
        return ok("whisper.cpp exists")
    if OS_NAME == "darwin":
        run_cmd(["brew", "install", "whisper-cpp"])
    else:
        run_cmd(["git", "clone", "--depth", "1", "https://github.com/ggerganov/whisper.cpp.git", "/tmp/whisper.cpp"])
        run_cmd(["make", "-j", str(os.cpu_count())], cwd="/tmp/whisper.cpp")
        run_cmd(["sudo", "cp", "/tmp/whisper.cpp/main", "/usr/local/bin/whisper-cpp"])

def download_models():
    log("Downloading models...")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    PIPER_DIR.mkdir(parents=True, exist_ok=True)

    download(
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
        MODELS_DIR / "ggml-base.en.bin"
    )

    for voice in ["en_US-lessac-medium", "en_US-amy-low", "en_US-libritts-medium"]:
        download(
            f"https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/{voice.replace('-', '/')}/{voice}.onnx",
            PIPER_DIR / f"{voice}.onnx"
        )
        download(
            f"https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/{voice.replace('-', '/')}/{voice}.onnx.json",
            PIPER_DIR / f"{voice}.onnx.json"
        )

def check_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        warn("Creating .env template...")
        env_file.write_text("""# ModelX Voice Assistant
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-20250514
OPENAI_API_KEY=your_key_here
EMBEDDING_MODEL=text-embedding-3-large
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=agent_platform
POSTGRES_USER=agent
POSTGRES_PASSWORD=agent_password
QDRANT_URL=http://localhost:6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j_password
REDIS_URL=redis://localhost:6379/0
""")
        err("Edit .env with your API keys, then re-run")

def start_dbs():
    log("Starting databases...")
    compose = ROOT / "docker-compose.yml"
    if has_cmd("docker") and compose.exists():
        run_cmd(["docker-compose", "up", "-d", "postgres", "qdrant", "neo4j", "redis"], check=False)
    else:
        warn("Docker/compose not found - start DBs manually")

def run_migrations():
    log("Running migrations...")
    py = VENV_DIR / "bin" / "python"
    run_cmd([str(py), "-c", """
from src.config.settings import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from src.memory.episodic_memory import Base
import asyncio
async def m():
    s = get_settings()
    e = create_async_engine(s.database_url)
    async with e.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    await e.dispose()
    print("Done")
asyncio.run(m())
"""], check=False)

def run_server(dev):
    log(f"Starting server on port {PORT}...")
    py = VENV_DIR / "bin" / "python"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT}:{env.get('PYTHONPATH', '')}"
    cmd = [str(py), "-m", "uvicorn", "src.voice_assistant.server:app",
           "--host", "0.0.0.0", "--port", str(PORT)]
    if dev: cmd.append("--reload")
    os.execvpe(str(py), cmd, env)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--skip-deps", action="store_true")
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    global PORT
    PORT = args.port

    print(f"""{C.B}
╔═══════════════════════════════════════════════════════════════╗
║         ModelX Voice Assistant - One-Command Runner         ║
║  🎤 Whisper STT  🔊 Piper TTS (female)  🧠 ModelX Brain     ║
╚═══════════════════════════════════════════════════════════════╝{C.X}
""")

    if not args.skip_deps:
        install_system()
        setup_venv()
        install_python_deps()
        install_piper()
        install_whisper_cpp()
    else:
        log("Skipping deps")

    if not args.skip_models:
        download_models()
    else:
        log("Skipping models")

    check_env()
    start_dbs()
    run_migrations()

    ok("Setup complete!")
    print(f"{C.G}▶ Open http://localhost:{PORT}{C.X}")
    print(f"{C.G}▶ Press Ctrl+C to stop{C.X}\n")

    run_server(args.dev)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.Y}Stopped{C.X}")