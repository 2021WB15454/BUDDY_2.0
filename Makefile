# Development Setup and Build System

.PHONY: help setup dev build test clean install-deps

# Default target
help:
	@echo "BUDDY Development Commands:"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup          - Initial project setup"
	@echo "  make install-deps   - Install all dependencies"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev            - Start development environment"
	@echo "  make dev-desktop    - Start desktop app in dev mode"
	@echo "  make dev-mobile     - Start mobile app in dev mode"
	@echo "  make dev-hub        - Start hub in dev mode"
	@echo ""
	@echo "Build Commands:"
	@echo "  make build          - Build all platforms"
	@echo "  make build-desktop  - Build desktop app"
	@echo "  make build-mobile   - Build mobile app"
	@echo "  make build-hub      - Build hub Docker image"
	@echo ""
	@echo "Test Commands:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests"
	@echo "  make test-e2e       - Run end-to-end tests"
	@echo "  make test-voice     - Run voice pipeline tests"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make models         - Download AI models"
	@echo "  make lint           - Run linting on all code"

# Setup and Installation
setup: install-deps models
	@echo "🚀 BUDDY setup complete!"

install-deps:
	@echo "📦 Installing dependencies..."
	# Python dependencies
	cd packages/core && pip install -r requirements.txt
	cd packages/voice && pip install -r requirements.txt
	cd packages/nlu && pip install -r requirements.txt
	cd packages/skills && pip install -r requirements.txt
	cd packages/sync && pip install -r requirements.txt
	cd packages/memory && pip install -r requirements.txt
	# Node.js dependencies
	cd apps/desktop && npm install
	cd apps/web && npm install
	# Flutter dependencies
	cd apps/mobile && flutter pub get

# Development
dev:
	@echo "🔧 Starting BUDDY development environment..."
	# Start core backend
	cd packages/core && python -m buddy.main &
	# Start desktop app
	cd apps/desktop && npm run dev &
	@echo "✅ Development environment started!"

dev-desktop:
	cd apps/desktop && npm run dev

dev-mobile:
	cd apps/mobile && flutter run

dev-hub:
	cd apps/hub && docker-compose up --build

# Building
build: build-desktop build-mobile build-hub

build-desktop:
	@echo "🏗️ Building desktop app..."
	cd apps/desktop && npm run build

build-mobile:
	@echo "📱 Building mobile app..."
	cd apps/mobile && flutter build apk
	cd apps/mobile && flutter build ios

build-hub:
	@echo "🏠 Building hub Docker image..."
	cd apps/hub && docker build -t buddy-hub .

# Testing
test: test-unit test-e2e

test-unit:
	@echo "🧪 Running unit tests..."
	cd packages/core && python -m pytest tests/
	cd packages/voice && python -m pytest tests/
	cd packages/nlu && python -m pytest tests/
	cd packages/skills && python -m pytest tests/
	cd packages/sync && python -m pytest tests/
	cd packages/memory && python -m pytest tests/

test-e2e:
	@echo "🎭 Running end-to-end tests..."
	cd tools/test && python -m pytest e2e/

test-voice:
	@echo "🎤 Running voice pipeline tests..."
	cd packages/voice && python -m pytest tests/test_pipeline.py -v

# Models
models:
	@echo "🤖 Downloading AI models..."
	cd tools/build && python download_models.py

# Utilities
clean:
	@echo "🧹 Cleaning build artifacts..."
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	rm -rf apps/desktop/dist/
	rm -rf apps/mobile/build/
	rm -rf apps/hub/dist/

lint:
	@echo "✨ Running linting..."
	cd packages/core && flake8 buddy/
	cd packages/voice && flake8 buddy_voice/
	cd packages/nlu && flake8 buddy_nlu/
	cd apps/desktop && npm run lint
	cd apps/mobile && flutter analyze

# Development shortcuts
logs:
	@echo "📋 Showing logs..."
	tail -f logs/buddy.log

restart:
	@echo "🔄 Restarting services..."
	pkill -f "buddy.main" || true
	make dev

# Docker shortcuts
docker-build:
	docker build -t buddy-hub apps/hub/

docker-run:
	docker run -p 8080:8080 -p 9090:9090 buddy-hub

docker-stop:
	docker stop $$(docker ps -q --filter ancestor=buddy-hub) || true
