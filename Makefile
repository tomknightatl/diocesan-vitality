# Makefile for USCCB Project
# Simple commands to help with development and deployment

.PHONY: help test build push deploy clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make test          - Run Python tests"
	@echo "  make build         - Build Docker images locally"
	@echo "  make push          - Push Docker images to registry"
	@echo "  make run-local     - Run application locally with docker-compose"
	@echo "  make stop-local    - Stop local docker-compose"
	@echo "  make deploy-dev    - Deploy to dev environment"
	@echo "  make deploy-prod   - Deploy to production environment"
	@echo "  make clean         - Clean up Docker resources"

# Load environment variables
include .env
export

# Variables
DOCKER_REPO := $(DOCKER_USERNAME)/usccb
BACKEND_IMAGE := $(DOCKER_REPO):backend
FRONTEND_IMAGE := $(DOCKER_REPO):frontend
GIT_SHA := $(shell git rev-parse --short HEAD)
BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

# Run tests
test:
	@echo "Running Python tests..."
	pytest tests/ -v

# Build Docker images locally
build:
	@echo "Building backend image..."
	docker build -t $(BACKEND_IMAGE)-local ./backend
	@echo "Building frontend image..."
	docker build -t $(FRONTEND_IMAGE)-local ./frontend

# Build and tag images for pushing
build-push: build
	@echo "Tagging images for push..."
	docker tag $(BACKEND_IMAGE)-local $(BACKEND_IMAGE)-$(GIT_SHA)
	docker tag $(FRONTEND_IMAGE)-local $(FRONTEND_IMAGE)-$(GIT_SHA)
	@if [ "$(BRANCH)" = "main" ]; then \
		docker tag $(BACKEND_IMAGE)-local $(BACKEND_IMAGE)-latest; \
		docker tag $(FRONTEND_IMAGE)-local $(FRONTEND_IMAGE)-latest; \
	elif [ "$(BRANCH)" = "develop" ]; then \
		docker tag $(BACKEND_IMAGE)-local $(BACKEND_IMAGE)-develop; \
		docker tag $(FRONTEND_IMAGE)-local $(FRONTEND_IMAGE)-develop; \
	fi

# Push images to Docker Hub
push: build-push
	@echo "Checking environment variables..."
	@if [ -z "$(DOCKER_USERNAME)" ] || [ -z "$(DOCKER_PASSWORD)" ]; then \
		echo "Error: DOCKER_USERNAME or DOCKER_PASSWORD not set"; \
		echo "Please run: source .env"; \
		exit 1; \
	fi
	@echo "Logging in to Docker Hub..."
	@echo $(DOCKER_PASSWORD) | docker login -u $(DOCKER_USERNAME) --password-stdin
	@echo "Pushing images..."
	docker push $(BACKEND_IMAGE)-$(GIT_SHA)
	docker push $(FRONTEND_IMAGE)-$(GIT_SHA)
	@if [ "$(BRANCH)" = "main" ]; then \
		docker push $(BACKEND_IMAGE)-latest; \
		docker push $(FRONTEND_IMAGE)-latest; \
	elif [ "$(BRANCH)" = "develop" ]; then \
		docker push $(BACKEND_IMAGE)-develop; \
		docker push $(FRONTEND_IMAGE)-develop; \
	fi

# Run locally with docker-compose
run-local:
	@echo "Starting local development environment..."
	docker-compose up -d
	@echo "Application running at:"
	@echo "  Frontend: http://localhost:8080"
	@echo "  Backend:  http://localhost:8000"

# Stop local environment
stop-local:
	@echo "Stopping local development environment..."
	docker-compose down

# Deploy to dev (manual trigger of GitHub Action)
deploy-dev:
	@echo "Triggering deployment to dev environment..."
	gh workflow run cd.yml -f environment=dev -f image_tag=develop

# Deploy to production (manual trigger of GitHub Action)
deploy-prod:
	@echo "Triggering deployment to production environment..."
	@read -p "Are you sure you want to deploy to production? (y/N) " confirm && \
	if [ "$$confirm" = "y" ]; then \
		gh workflow run cd.yml -f environment=prod -f image_tag=latest; \
	else \
		echo "Deployment cancelled."; \
	fi

# Clean up Docker resources
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f