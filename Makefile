# USCCB Development Makefile
# Quick commands for local development

.PHONY: help dev test quick clean install start stop

help: ## Show this help message
	@echo "USCCB Development Commands"
	@echo "========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	@if [ -d "frontend" ]; then \
		echo "📦 Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi
	@echo "✅ Dependencies installed"

start: ## Start development services
	@echo "🚀 Starting development environment..."
	@python scripts/dev_start.py --backend-only

start-full: ## Start backend and frontend
	@echo "🚀 Starting full development environment..."
	@python scripts/dev_start.py

stop: ## Stop development services
	@echo "🛑 Stopping services..."
	@lsof -ti:8000 | xargs -r kill
	@lsof -ti:3000 | xargs -r kill
	@echo "✅ Services stopped"

test: ## Run all development tests
	@echo "🧪 Running development tests..."
	@python scripts/dev_test.py --all

test-quick: ## Run quick tests
	@echo "🧪 Running quick tests..."
	@python scripts/dev_test.py --db --ai --env

dev: ## Quick development setup check
	@echo "🔍 Development environment check..."
	@python scripts/dev_test.py --env
	@python scripts/dev_quick.py stats

extract: ## Quick single parish extraction test
	@echo "🏃‍♂️ Quick extraction test..."
	@python scripts/dev_quick.py extract

diocese: ## Quick diocese scan test
	@echo "🔍 Quick diocese scan..."
	@python scripts/dev_quick.py diocese

schedule: ## Quick schedule extraction test
	@echo "⏰ Quick schedule test..."
	@python scripts/dev_quick.py schedule

logs: ## View recent logs
	@python scripts/dev_quick.py logs

stats: ## Show database statistics
	@python scripts/dev_quick.py stats

clean: ## Clean cache and temporary files
	@echo "🧹 Cleaning cache and temporary files..."
	@python scripts/dev_quick.py clear-cache
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache
	@echo "✅ Cleanup complete"

kill-chrome: ## Kill stuck Chrome processes
	@python scripts/dev_quick.py kill-chrome

restart: ## Restart all services
	@python scripts/dev_quick.py restart

ports: ## Check development port usage
	@python scripts/dev_quick.py ports

pipeline: ## Run full pipeline with monitoring (small test)
	@echo "🚀 Running pipeline test..."
	@python run_pipeline_monitored.py \
		--diocese_id 1 \
		--max_parishes_per_diocese 5 \
		--num_parishes_for_schedule 2 \
		--monitoring_url http://localhost:8000

pipeline-single: ## Run pipeline for single diocese
	@echo "🚀 Running single diocese pipeline..."
	@python run_pipeline_monitored.py \
		--diocese_id $(DIOCESE_ID) \
		--max_parishes_per_diocese 10 \
		--skip_schedules \
		--monitoring_url http://localhost:8000

format: ## Format code with black
	@echo "🎨 Formatting code..."
	@black . --exclude="venv|node_modules"
	@echo "✅ Code formatted"

lint: ## Run linting
	@echo "🔍 Running linting..."
	@flake8 . --exclude=venv,node_modules --max-line-length=88 --extend-ignore=E203,W503
	@echo "✅ Linting complete"

env-check: ## Check environment configuration
	@python scripts/dev_test.py --env

db-check: ## Test database connection
	@python scripts/dev_test.py --db

ai-check: ## Test AI API connection
	@python scripts/dev_test.py --ai

webdriver-check: ## Test Chrome WebDriver
	@python scripts/dev_test.py --webdriver

monitor-check: ## Test monitoring integration
	@python scripts/dev_test.py --monitoring

# Infrastructure Commands
# =======================

infra-setup: ## Set up complete infrastructure (all 4 steps)
	@echo "🚀 Setting up complete infrastructure..."
	@$(MAKE) cluster-create
	@$(MAKE) argocd-install
	@$(MAKE) argocd-apps
	@$(MAKE) tunnel-create
	@echo "🎉 Infrastructure setup complete!"

cluster-create: ## Step 1: Create cluster and kubectl context
	@echo "🚀 Step 1: Creating cluster and kubectl context..."
	@cd terraform/environments/dev && \
		export DIGITALOCEAN_TOKEN=$$(grep DIGITALOCEAN_TOKEN ../../../.env | cut -d'=' -f2) && \
		terraform init && \
		terraform apply -target=module.k8s_cluster -auto-approve && \
		doctl kubernetes cluster kubeconfig save dv-dev && \
		kubectl config use-context do-nyc2-dv-dev && \
		kubectl get nodes
	@echo "✅ Step 1 Complete: Cluster created"

argocd-install: ## Step 2: Install ArgoCD and configure repository
	@echo "🚀 Step 2: Installing ArgoCD..."
	@kubectl config use-context do-nyc2-dv-dev && \
		kubectl create namespace argocd && \
		kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml && \
		kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s && \
		kubectl patch configmap argocd-cm -n argocd --patch '{"data":{"repositories":"- url: https://github.com/t-k-/diocesan-vitality.git"}}'
	@echo "✅ Step 2 Complete: ArgoCD installed"
	@echo "   Admin password: $$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)"

argocd-apps: ## Step 3: Install ArgoCD ApplicationSets
	@echo "🚀 Step 3: Installing ArgoCD ApplicationSets..."
	@kubectl config use-context do-nyc2-dv-dev && \
		kubectl apply -f k8s/argocd/sealed-secrets-multi-env-applicationset.yaml && \
		kubectl apply -f k8s/argocd/cloudflare-tunnel-multi-env-applicationset.yaml && \
		kubectl apply -f k8s/argocd/diocesan-vitality-environments-applicationset.yaml
	@echo "✅ Step 3 Complete: ApplicationSets installed"

tunnel-create: ## Step 4: Create Cloudflare tunnel and DNS records
	@echo "🚀 Step 4: Creating Cloudflare tunnel..."
	@cd terraform/environments/dev && \
		export CLOUDFLARE_API_TOKEN=$$(grep CLOUDFLARE_API_TOKEN ../../../.env | cut -d'=' -f2) && \
		terraform apply -target=module.cloudflare_tunnel -auto-approve
	@echo "✅ Step 4 Complete: Cloudflare tunnel created"

infra-status: ## Check infrastructure status
	@echo "🔍 Infrastructure Status:"
	@echo "========================"
	@echo "Kubectl contexts:"
	@kubectl config get-contexts | grep -E "(CURRENT|do-nyc2)" || echo "  No dev contexts found"
	@echo ""
	@echo "ArgoCD status:"
	@kubectl get pods -n argocd 2>/dev/null | grep -E "(NAME|argocd-server)" || echo "  ArgoCD not installed"
	@echo ""
	@echo "Applications:"
	@kubectl get applications -n argocd 2>/dev/null || echo "  No applications found"
	@echo ""
	@echo "Tunnel status:"
	@cd terraform/environments/dev && terraform output tunnel_info 2>/dev/null || echo "  No tunnel found"

infra-destroy: ## Destroy complete infrastructure
	@echo "🧹 Destroying infrastructure..."
	@$(MAKE) tunnel-destroy
	@$(MAKE) argocd-destroy
	@$(MAKE) cluster-destroy
	@echo "✅ Infrastructure destroyed"

tunnel-destroy: ## Destroy Cloudflare tunnel
	@echo "🧹 Destroying Cloudflare tunnel..."
	@cd terraform/environments/dev && \
		export CLOUDFLARE_API_TOKEN=$$(grep CLOUDFLARE_API_TOKEN ../../../.env | cut -d'=' -f2) && \
		terraform destroy -target=module.cloudflare_tunnel -auto-approve || true

argocd-destroy: ## Destroy ArgoCD
	@echo "🧹 Destroying ArgoCD..."
	@kubectl delete namespace argocd --ignore-not-found=true

cluster-destroy: ## Destroy cluster
	@echo "🧹 Destroying cluster..."
	@cd terraform/environments/dev && \
		export DIGITALOCEAN_TOKEN=$$(grep DIGITALOCEAN_TOKEN ../../../.env | cut -d'=' -f2) && \
		terraform destroy -target=module.k8s_cluster -auto-approve || true
