# ModelX Voice Assistant - Development Makefile

.PHONY: help install install-dev test test-unit test-integration lint format typecheck clean build publish docs

# Default target
help:
	@echo "ModelX Voice Assistant - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install package in development mode"
	@echo "  make install-dev    Install with all dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all tests"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-integration  Run integration tests"
	@echo "  make test-audio     Run audio hardware tests (requires mic/speakers)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run all linters (ruff, mypy)"
	@echo "  make format         Format code (black, isort)"
	@echo "  make typecheck      Run mypy type checking"
	@echo ""
	@echo "Build & Publish:"
	@echo "  make build          Build distribution packages"
	@echo "  make publish-test   Publish to TestPyPI"
	@echo "  make publish        Publish to PyPI"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run Docker container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          Clean build artifacts"
	@echo "  make deps-update    Update dependencies"
	@echo "  make deps-audit     Security audit dependencies"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest -v --tb=short

test-unit:
	pytest tests/unit/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short -k "not audio"

test-audio:
	pytest tests/ -v --tb=short -k "audio"

test-coverage:
	pytest --cov=modelx_voice --cov-report=html --cov-report=term-missing

# Code Quality
lint: ruff mypy

ruff:
	ruff check modelx_voice/ tests/

mypy:
	mypy modelx_voice/

format: black isort

black:
	black modelx_voice/ tests/

isort:
	isort modelx_voice/ tests/

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Build
build: clean
	python -m build

build-check:
	twine check dist/*

# Publishing
publish-test: build build-check
	twine upload --repository testpypi dist/*

publish: build build-check
	twine upload dist/*

# Docker
docker-build:
	docker build -t modelx/voice:latest .

docker-run:
	docker run -it --rm --device=/dev/snd \
	  -v ~/.modelx-voice:/root/.modelx-voice \
	  modelx/voice:latest

# Documentation
docs:
	@echo "Documentation is in README.md, ARCHITECTURE.md, CONTRIBUTING.md"

# Maintenance
clean:
	rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

deps-update:
	pip install --upgrade pip
	pip install --upgrade -e ".[dev]"
	pip list --outdated

deps-audit:
	pip install pip-audit
	pip-audit --desc

# Development helpers
run:
	python -m modelx_voice.main

run-setup:
	python -m modelx_voice.main --setup

run-test-audio:
	python -m modelx_voice.main --test-audio

run-test-api:
	python -m modelx_voice.main --test-api

# Voice model download
download-voices:
	python -c "from modelx_voice.voices.downloader import download_all_voices; import asyncio; asyncio.run(download_all_voices())"

# Check installation
check-install:
	python -c "import modelx_voice; print('Version:', modelx_voice.__version__)"
	python -c "from modelx_voice.audio import AudioCapture; print('Audio OK')"
	python -c "from modelx_voice.stt import WhisperTranscriber; print('STT OK')"
	python -c "from modelx_voice.tts import PiperSynthesizer; print('TTS OK')"
	python -c "from modelx_voice.brain import ModelXBrain; print('Brain OK')"
	python -c "from modelx_voice.config import ConfigManager; print('Config OK')"
	python -c "from modelx_voice.ui import SimpleVoiceUI; print('UI OK')"
	python -c "from modelx_voice.pipeline import AudioPipeline; print('Pipeline OK')"

# Version bump helpers
version-patch:
	bump2version patch

version-minor:
	bump2version minor

version-major:
	bump2version major