# USCCB Development Makefile
# Quick commands for local development

.PHONY: help dev test quick clean install start stop \
	db-reset db-migrate db-deploy db-backup db-test \
	db-status db-validate db-rollback db-dev \
	reset migrate deploy backup test-db status validate rollback dev-db

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

infra-setup: ## Set up complete infrastructure (8 core steps, usage: make infra-setup CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Setting up complete infrastructure for '$$CLUSTER_LABEL'..." && \
	echo "📋 Executing 8-step infrastructure setup:" && \
	echo "   Steps 1-4: Cluster (Auth → Check → Create → Context)" && \
	echo "   Steps 5-8: Tunnel (Auth → Check → Create → DNS)" && \
	$(MAKE) cluster-auth && \
	$(MAKE) cluster-check CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) cluster-create CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) cluster-context CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) tunnel-auth && \
	$(MAKE) tunnel-check CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) tunnel-create CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) tunnel-dns CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "✅ Core infrastructure setup complete (Steps 1-8)!" && \
	echo "🔄 Proceeding with ArgoCD and applications..." && \
	$(MAKE) argocd-install CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) argocd-apps CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) sealed-secrets-create CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) tunnel-test CLUSTER_LABEL=$$CLUSTER_LABEL && \
	if [ "$$CLUSTER_LABEL" = "dev" ]; then \
		echo "🗄️  Initializing dev database..." && \
		echo "   Step 1: Extracting production schema to sql/initial_schema.sql" && \
		$(MAKE) database-schema-refresh && \
		echo "   Step 2: Applying schema and copying data to dev database" && \
		$(MAKE) database-init-dev; \
	fi && \
	echo "🔍 Running final infrastructure verification..." && \
	$(MAKE) infra-verify CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "🎉 Complete infrastructure setup finished for $$CLUSTER_LABEL!"

infra-destroy: ## Destroy complete infrastructure (usage: make infra-destroy CLUSTER_LABEL=dev [FORCE=yes])
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	FORCE=$${FORCE:-no} && \
	CLUSTER_NAME="dv-$$CLUSTER_LABEL" && \
	echo "🚨 DESTRUCTIVE: Destroying complete infrastructure for '$$CLUSTER_LABEL'..." && \
	echo "⚠️  This will permanently delete:" && \
	echo "   - DigitalOcean cluster: $$CLUSTER_NAME" && \
	echo "   - Cloudflare tunnel: do-nyc2-dv-$$CLUSTER_LABEL" && \
	echo "   - DNS records for $$CLUSTER_LABEL.{ui,api,argocd}.diocesanvitality.org" && \
	echo "   - kubectl context: do-nyc2-dv-$$CLUSTER_LABEL" && \
	if [ "$$FORCE" != "yes" ]; then \
		read -p "Are you sure? Type 'yes' to continue: " CONFIRM </dev/tty && \
		if [ "$$CONFIRM" != "yes" ]; then \
			echo "❌ Operation cancelled"; \
			exit 1; \
		fi; \
	else \
		echo "⚡ FORCE=yes detected - skipping confirmation"; \
	fi && \
	echo "🗑️  Executing infrastructure destruction (optimized order: Cluster → Context → Tunnel → DNS)..." && \
	echo "" && \
	echo "📍 Step 1/4: Destroying cluster..." && \
	$(MAKE) cluster-destroy CLUSTER_LABEL=$$CLUSTER_LABEL FORCE=yes || true && \
	echo "" && \
	echo "📍 Step 2/4: Cleaning kubectl context..." && \
	$(MAKE) cluster-context-destroy CLUSTER_LABEL=$$CLUSTER_LABEL || true && \
	echo "" && \
	echo "📍 Step 3/4: Destroying Cloudflare tunnel..." && \
	$(MAKE) tunnel-destroy CLUSTER_LABEL=$$CLUSTER_LABEL FORCE=yes || true && \
	echo "" && \
	echo "📍 Step 4/4: Destroying DNS records..." && \
	$(MAKE) tunnel-dns-destroy CLUSTER_LABEL=$$CLUSTER_LABEL || true && \
	echo "" && \
	echo "🔍 Verifying infrastructure destruction..." && \
	if $(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster get $$CLUSTER_NAME" 2>/dev/null | grep -q "$$CLUSTER_NAME"; then \
		echo "⚠️  Warning: Cluster $$CLUSTER_NAME still exists!"; \
	else \
		echo "✅ Cluster $$CLUSTER_NAME confirmed deleted"; \
	fi && \
	if kubectl config get-contexts -o name 2>/dev/null | grep -q "^do-nyc2-dv-$$CLUSTER_LABEL$$"; then \
		echo "⚠️  Warning: kubectl context still exists!"; \
	else \
		echo "✅ kubectl context confirmed removed"; \
	fi && \
	echo "" && \
	echo "✅ Infrastructure destruction complete for $$CLUSTER_LABEL"

infra-verify: ## Verify infrastructure is working (usage: make infra-verify CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔍 Verifying infrastructure for '$$CLUSTER_LABEL'..." && \
	echo "" && \
	echo "Testing URLs:" && \
	echo "  UI:     https://$$CLUSTER_LABEL.ui.diocesanvitality.org" && \
	echo "  API:    https://$$CLUSTER_LABEL.api.diocesanvitality.org" && \
	echo "  ArgoCD: https://$$CLUSTER_LABEL.argocd.diocesanvitality.org" && \
	echo "" && \
	UI_STATUS=$$(curl -s -o /dev/null -w "%{http_code}" https://$$CLUSTER_LABEL.ui.diocesanvitality.org 2>/dev/null || echo "000") && \
	API_STATUS=$$(curl -s -o /dev/null -w "%{http_code}" https://$$CLUSTER_LABEL.api.diocesanvitality.org/health 2>/dev/null || echo "000") && \
	ARGOCD_STATUS=$$(curl -s -o /dev/null -w "%{http_code}" https://$$CLUSTER_LABEL.argocd.diocesanvitality.org 2>/dev/null || echo "000") && \
	echo "Results:" && \
	if [ "$$UI_STATUS" = "200" ] || [ "$$UI_STATUS" = "301" ] || [ "$$UI_STATUS" = "302" ]; then \
		echo "  ✅ UI: $$UI_STATUS"; \
	else \
		echo "  ⚠️  UI: $$UI_STATUS (may still be deploying)"; \
	fi && \
	if [ "$$API_STATUS" = "200" ]; then \
		echo "  ✅ API: $$API_STATUS"; \
	else \
		echo "  ⚠️  API: $$API_STATUS (may still be deploying)"; \
	fi && \
	if [ "$$ARGOCD_STATUS" = "200" ] || [ "$$ARGOCD_STATUS" = "307" ]; then \
		echo "  ✅ ArgoCD: $$ARGOCD_STATUS"; \
	else \
		echo "  ⚠️  ArgoCD: $$ARGOCD_STATUS (may still be deploying)"; \
	fi && \
	echo "" && \
	if [ "$$UI_STATUS" != "000" ] && [ "$$API_STATUS" != "000" ] && [ "$$ARGOCD_STATUS" != "000" ]; then \
		echo "✅ Infrastructure verification complete - all services responding"; \
	else \
		echo "⚠️  Some services may still be deploying. Run 'make infra-verify CLUSTER_LABEL=$$CLUSTER_LABEL' again in a few minutes"; \
	fi

cluster-auth: ## Step a: A5uthenticate with DigitalOcean (usage: make cluster-auth)
	@echo "🔍 Step a: Setting up DigitalOcean authentication..." && \
	if [ ! -f .env ]; then \
		echo "❌ .env file not found. Please copy .env.example to .env and configure your tokens" && \
		exit 1; \
	fi && \
	DIGITALOCEAN_TOKEN=$$(sed -n 's/^DIGITALOCEAN_TOKEN=//p' .env | tr -d '\r\n"'"'"'') && \
	if [ -z "$$DIGITALOCEAN_TOKEN" ] || [ "$$DIGITALOCEAN_TOKEN" = "<key>" ]; then \
		echo "❌ DIGITALOCEAN_TOKEN not set in .env file. Please add your DigitalOcean API token" && \
		exit 1; \
	fi && \
	echo "🔐 Authenticating doctl with token from .env..." && \
	echo "🧪 Testing DigitalOcean API connectivity..." && \
	if timeout 5 curl -s --connect-timeout 3 https://api.digitalocean.com/v2 >/dev/null 2>&1; then \
		echo "✅ DigitalOcean API is reachable" && \
		echo "🧪 Testing doctl authentication..." && \
		if DIGITALOCEAN_ACCESS_TOKEN="$$DIGITALOCEAN_TOKEN" timeout 5 doctl auth list >/dev/null 2>&1; then \
			echo "✅ Step a Complete: doctl authentication verified - can access DigitalOcean account"; \
		else \
			echo "❌ doctl authentication failed - token may be invalid or API is experiencing issues" && \
			exit 1; \
		fi; \
	else \
		echo "❌ DigitalOcean API is not reachable - cannot authenticate without API access" && \
		exit 1; \
	fi

cluster-check: ## Step b: Check if cluster exists (usage: make cluster-check CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔍 Step b: Checking if cluster exists..." && \
	CLUSTER_NAME="dv-$$CLUSTER_LABEL" && \
	$(MAKE) cluster-auth && \
	echo "🔍 Querying cluster $$CLUSTER_NAME..." && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster get $$CLUSTER_NAME" && \
	echo "✅ Step b Complete: Cluster $$CLUSTER_NAME exists and is accessible"

_doctl-exec: ## Internal helper to execute doctl commands with authentication
	@DIGITALOCEAN_TOKEN=$$(sed -n 's/^DIGITALOCEAN_TOKEN=//p' .env | tr -d '\r\n"'\''') && \
	DIGITALOCEAN_ACCESS_TOKEN="$$DIGITALOCEAN_TOKEN" timeout 900 doctl $(DOCTL_CMD)

cluster-create: ## Step c: Create cluster (usage: make cluster-create CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step c: Creating DigitalOcean cluster for '$$CLUSTER_LABEL'..." && \
	CLUSTER_NAME="dv-$$CLUSTER_LABEL" && \
	$(MAKE) cluster-check CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "✅ Step c Complete: Cluster $$CLUSTER_NAME already exists - skipping creation" || { \
		REGION="nyc2" && \
		echo "🔍 Checking available Kubernetes versions..." && \
		AVAILABLE_VERSIONS=$$($(MAKE) _doctl-exec DOCTL_CMD="kubernetes options versions --format Slug --no-header" 2>/dev/null) && \
		REQUESTED_MINOR="1.33" && \
		K8S_VERSION=$$(echo "$$AVAILABLE_VERSIONS" | grep "^$$REQUESTED_MINOR" | head -1) && \
		if [ -z "$$K8S_VERSION" ]; then \
			echo "⚠️  Warning: No version matching $$REQUESTED_MINOR found, using latest available" && \
			K8S_VERSION=$$(echo "$$AVAILABLE_VERSIONS" | head -1); \
		fi && \
		echo "✅ Selected Kubernetes version: $$K8S_VERSION" && \
		echo "📋 Cluster configuration (matching production):" && \
		echo "   Name: $$CLUSTER_NAME" && \
		echo "   Region: $$REGION" && \
		echo "   Kubernetes version: $$K8S_VERSION" && \
		echo "   Node pools:" && \
		echo "     - slow-pool: s-1vcpu-2gb (1 node)" && \
		echo "     - fast-pool: s-2vcpu-4gb (2 nodes)" && \
		echo "   Auto-upgrade: false" && \
		echo "   HA Control Plane: false" && \
		echo "🏗️  Creating cluster $$CLUSTER_NAME with dual node pools..." && \
		echo "🚀 Starting cluster creation (this may take 5-10 minutes)..." && \
		$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster create $$CLUSTER_NAME --region $$REGION --version $$K8S_VERSION --node-pool 'name=slow-pool;size=s-1vcpu-2gb;count=1' --node-pool 'name=fast-pool;size=s-2vcpu-4gb;count=2' --auto-upgrade=false --ha=false --tag environment:$$CLUSTER_LABEL --tag project:diocesan-vitality" & \
		CREATE_PID=$$! && \
		echo "🔍 Monitoring cluster creation progress..." && \
		while kill -0 $$CREATE_PID 2>/dev/null; do \
			if CURRENT_STATUS=$$($(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster get $$CLUSTER_NAME --format Status --no-header" 2>/dev/null); then \
				echo "📊 Cluster status: $$CURRENT_STATUS ($$(date '+%H:%M:%S'))"; \
			else \
				echo "⏳ Cluster initializing... ($$(date '+%H:%M:%S'))"; \
			fi; \
			sleep 30; \
		done && \
		wait $$CREATE_PID && \
		echo "✅ Cluster creation process completed!" && \
		echo "🔍 Verifying final cluster status..." && \
		FINAL_STATUS=$$($(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster get $$CLUSTER_NAME --format Status --no-header" 2>/dev/null) && \
		echo "📊 Final cluster status: $$FINAL_STATUS" && \
		if [ "$$FINAL_STATUS" = "running" ]; then \
			echo "✅ Step c Complete: Cluster is running and ready!"; \
			CLUSTER_ID=$$($(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster get $$CLUSTER_NAME --format ID --no-header" 2>/dev/null) && \
			echo "🔢 Cluster ID: $$CLUSTER_ID"; \
		else \
			echo "⚠️  Cluster status is $$FINAL_STATUS - may still be initializing"; \
			echo "✅ Step c Complete: Cluster creation initiated"; \
		fi; \
	}

cluster-destroy: ## Step d: Destroy cluster (usage: make cluster-destroy CLUSTER_LABEL=dev [FORCE=yes])
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	FORCE=$${FORCE:-no} && \
	echo "🚨 Step d: DESTRUCTIVE - Destroying DigitalOcean cluster for '$$CLUSTER_LABEL'..." && \
	CLUSTER_NAME="dv-$$CLUSTER_LABEL" && \
	echo "⚠️  This will permanently delete cluster: $$CLUSTER_NAME" && \
	if [ "$$FORCE" != "yes" ]; then \
		read -p "Are you sure? Type 'yes' to continue: " CONFIRM </dev/tty && \
		if [ "$$CONFIRM" != "yes" ]; then \
			echo "❌ Operation cancelled"; \
			exit 1; \
		fi; \
	fi && \
	if $(MAKE) cluster-check CLUSTER_LABEL=$$CLUSTER_LABEL 2>/dev/null; then \
		echo "🗑️  Deleting cluster $$CLUSTER_NAME (this may take several minutes)..." && \
		$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster delete $$CLUSTER_NAME --force" && \
		echo "🧹 Cleaning up sealed secrets from repository..." && \
		$(MAKE) _cleanup-sealed-secrets CLUSTER_LABEL=$$CLUSTER_LABEL && \
		echo "✅ Step d Complete: Cluster $$CLUSTER_NAME deleted successfully"; \
	else \
		echo "ℹ️  Step d Complete: Cluster $$CLUSTER_NAME does not exist - nothing to destroy"; \
	fi

cluster-context: ## Step e: Setup kubectl context (usage: make cluster-context CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔧 Step e: Setting up kubectl context for '$$CLUSTER_LABEL'..." && \
	CLUSTER_NAME="dv-$$CLUSTER_LABEL" && \
	$(MAKE) cluster-check CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "🔍 Attempting to save kubectl configuration..." && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster kubeconfig save $$CLUSTER_NAME" && \
	echo "✅ kubectl configuration saved successfully" && \
	if kubectl config get-contexts -o name | grep -q "^do-nyc2-dv-$$CLUSTER_LABEL$$"; then \
		echo "ℹ️  Context do-nyc2-dv-$$CLUSTER_LABEL already exists"; \
	else \
		kubectl config rename-context do-nyc2-$$CLUSTER_NAME do-nyc2-dv-$$CLUSTER_LABEL; \
	fi && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "🔍 Verifying cluster access..." && \
	kubectl cluster-info && \
	kubectl get nodes && \
	echo "✅ Step e Complete: kubectl context configured for $$CLUSTER_NAME"

cluster-context-destroy: ## Step f: Remove kubectl context (usage: make cluster-context-destroy CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🧹 Step f: Cleaning up kubectl context for '$$CLUSTER_LABEL'..." && \
	kubectl config delete-context do-nyc2-dv-$$CLUSTER_LABEL 2>/dev/null || true && \
	echo "✅ Step f Complete: kubectl context destroyed for $$CLUSTER_LABEL"

tunnel-auth: ## Step g: Authenticate with Cloudflare (usage: make tunnel-auth)
	@echo "🔍 Step g: Setting up Cloudflare authentication..." && \
	if [ ! -f .env ]; then \
		echo "❌ .env file not found. Please copy .env.example to .env and configure your tokens" && \
		exit 1; \
	fi && \
	CLOUDFLARE_API_TOKEN=$$(sed -n 's/^CLOUDFLARE_API_TOKEN=//p' .env | tr -d '\r\n"'"'"'') && \
	CLOUDFLARE_ACCOUNT_ID=$$(sed -n 's/^CLOUDFLARE_ACCOUNT_ID=//p' .env | tr -d '\r\n"'"'"'') && \
	ZONE_ID=$$(sed -n 's/^CLOUDFLARE_ZONE_ID=//p' .env | tr -d '\r\n"'"'"'') && \
	if [ -z "$$CLOUDFLARE_API_TOKEN" ] || [ -z "$$CLOUDFLARE_ACCOUNT_ID" ] || [ -z "$$ZONE_ID" ]; then \
		echo "❌ Missing Cloudflare credentials in .env file" && \
		echo "Required: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_ZONE_ID" && \
		exit 1; \
	fi && \
	echo "🔐 Authenticating with Cloudflare API..." && \
	export CLOUDFLARE_API_TOKEN="$$CLOUDFLARE_API_TOKEN" && \
	echo "🔍 Verifying Cloudflare authentication..." && \
	if curl -s -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
		-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" | jq -e '.success == true' >/dev/null 2>&1; then \
		echo "✅ Step g Complete: Cloudflare API authentication verified"; \
	else \
		echo "❌ Cloudflare API authentication failed. Please check your CLOUDFLARE_API_TOKEN in .env" && \
		exit 1; \
	fi

tunnel-check: ## Step h: Check if tunnel exists (usage: make tunnel-check CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔍 Step h: Checking if tunnel exists..." && \
	TUNNEL_NAME="do-nyc2-dv-$$CLUSTER_LABEL" && \
	$(MAKE) tunnel-auth && \
	CLOUDFLARE_API_TOKEN=$$(sed -n 's/^CLOUDFLARE_API_TOKEN=//p' .env | tr -d '\r\n"'"'"'') && \
	CLOUDFLARE_ACCOUNT_ID=$$(sed -n 's/^CLOUDFLARE_ACCOUNT_ID=//p' .env | tr -d '\r\n"'"'"'') && \
	export CLOUDFLARE_API_TOKEN="$$CLOUDFLARE_API_TOKEN" && \
	echo "🔧 Fetching tunnels via API..." && \
	TUNNELS_RESPONSE=$$(curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel" \
		-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
		-H "Content-Type: application/json") && \
	if TUNNEL_ID=$$(echo "$$TUNNELS_RESPONSE" | jq -r ".result[] | select(.name==\"$$TUNNEL_NAME\" and .deleted_at==null) | .id" 2>/dev/null | head -1) && [ -n "$$TUNNEL_ID" ] && [ "$$TUNNEL_ID" != "null" ]; then \
		echo "✅ Step h Complete: Tunnel $$TUNNEL_NAME exists with ID: $$TUNNEL_ID"; \
	else \
		echo "ℹ️  Step h Complete: Tunnel $$TUNNEL_NAME does not exist"; \
	fi

tunnel-create: ## Step i: Create tunnel (usage: make tunnel-create CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step i: Creating Cloudflare tunnel for '$$CLUSTER_LABEL'..." && \
	TUNNEL_NAME="do-nyc2-dv-$$CLUSTER_LABEL" && \
	$(MAKE) tunnel-check CLUSTER_LABEL=$$CLUSTER_LABEL && \
	CLOUDFLARE_API_TOKEN=$$(sed -n 's/^CLOUDFLARE_API_TOKEN=//p' .env | tr -d '\r\n"'"'"'') && \
	CLOUDFLARE_ACCOUNT_ID=$$(sed -n 's/^CLOUDFLARE_ACCOUNT_ID=//p' .env | tr -d '\r\n"'"'"'') && \
	export CLOUDFLARE_API_TOKEN="$$CLOUDFLARE_API_TOKEN" && \
	TUNNELS_RESPONSE=$$(curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel" \
		-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
		-H "Content-Type: application/json") && \
	if TUNNEL_ID=$$(echo "$$TUNNELS_RESPONSE" | jq -r ".result[] | select(.name==\"$$TUNNEL_NAME\" and .deleted_at==null) | .id" 2>/dev/null | head -1) && [ -n "$$TUNNEL_ID" ] && [ "$$TUNNEL_ID" != "null" ]; then \
		echo "✅ Step i Complete: Tunnel $$TUNNEL_NAME already exists with ID: $$TUNNEL_ID"; \
	else \
		echo "🏗️  Creating tunnel $$TUNNEL_NAME via API..." && \
		TUNNEL_CREATE_RESPONSE=$$(curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel" \
			-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
			-H "Content-Type: application/json" \
			--data "{\"name\":\"$$TUNNEL_NAME\",\"tunnel_secret\":\"$$(openssl rand -base64 32)\"}") && \
		echo "📄 Tunnel creation response: $$TUNNEL_CREATE_RESPONSE" && \
		TUNNEL_ID=$$(echo "$$TUNNEL_CREATE_RESPONSE" | jq -r '.result.id' 2>/dev/null) && \
		if [ -n "$$TUNNEL_ID" ] && [ "$$TUNNEL_ID" != "null" ]; then \
			echo "✅ Step i Complete: Tunnel created with ID: $$TUNNEL_ID"; \
		else \
			echo "❌ Failed to create tunnel" && \
			exit 1; \
		fi; \
	fi

tunnel-destroy: ## Step j: Destroy tunnel (usage: make tunnel-destroy CLUSTER_LABEL=dev [FORCE=yes])
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	FORCE=$${FORCE:-no} && \
	echo "🚨 Step j: DESTRUCTIVE - Destroying Cloudflare tunnel for '$$CLUSTER_LABEL'..." && \
	TUNNEL_NAME="do-nyc2-dv-$$CLUSTER_LABEL" && \
	echo "⚠️  This will permanently delete tunnel: $$TUNNEL_NAME" && \
	if [ "$$FORCE" != "yes" ]; then \
		read -p "Are you sure? Type 'yes' to continue: " CONFIRM </dev/tty && \
		if [ "$$CONFIRM" != "yes" ]; then \
			echo "❌ Operation cancelled"; \
			exit 1; \
		fi; \
	fi && \
	$(MAKE) tunnel-auth && \
	CLOUDFLARE_API_TOKEN=$$(sed -n 's/^CLOUDFLARE_API_TOKEN=//p' .env | tr -d '\r\n"'"'"'') && \
	CLOUDFLARE_ACCOUNT_ID=$$(sed -n 's/^CLOUDFLARE_ACCOUNT_ID=//p' .env | tr -d '\r\n"'"'"'') && \
	export CLOUDFLARE_API_TOKEN="$$CLOUDFLARE_API_TOKEN" && \
	echo "🔍 Checking if tunnel exists..." && \
	TUNNELS_RESPONSE=$$(curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel" \
		-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
		-H "Content-Type: application/json") && \
	if TUNNEL_ID=$$(echo "$$TUNNELS_RESPONSE" | jq -r ".result[] | select(.name==\"$$TUNNEL_NAME\" and .deleted_at==null) | .id" 2>/dev/null | head -1) && [ -n "$$TUNNEL_ID" ] && [ "$$TUNNEL_ID" != "null" ]; then \
		echo "🗑️  Deleting tunnel: $$TUNNEL_NAME (ID: $$TUNNEL_ID)" && \
		TUNNEL_DELETE_RESPONSE=$$(curl -s -X DELETE "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel/$$TUNNEL_ID" \
			-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN") && \
		if echo "$$TUNNEL_DELETE_RESPONSE" | jq -e '.success == true' >/dev/null 2>&1; then \
			echo "✅ Step j Complete: Tunnel $$TUNNEL_NAME ($$TUNNEL_ID) deleted successfully"; \
		else \
			echo "⚠️  Warning: Tunnel deletion response indicates issues"; \
			echo "📄 Response: $$TUNNEL_DELETE_RESPONSE"; \
		fi; \
	else \
		echo "ℹ️  Step j Complete: Tunnel $$TUNNEL_NAME does not exist or is already deleted"; \
	fi

tunnel-dns: ## Step k: Setup tunnel DNS and public hostnames (usage: make tunnel-dns CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🌐 Step k: Creating DNS records and public hostnames for '$$CLUSTER_LABEL'..." && \
	TUNNEL_NAME="do-nyc2-dv-$$CLUSTER_LABEL" && \
	$(MAKE) tunnel-check CLUSTER_LABEL=$$CLUSTER_LABEL && \
	CLOUDFLARE_API_TOKEN=$$(sed -n 's/^CLOUDFLARE_API_TOKEN=//p' .env | tr -d '\r\n"'"'"'') && \
	CLOUDFLARE_ACCOUNT_ID=$$(sed -n 's/^CLOUDFLARE_ACCOUNT_ID=//p' .env | tr -d '\r\n"'"'"'') && \
	ZONE_ID=$$(sed -n 's/^CLOUDFLARE_ZONE_ID=//p' .env | tr -d '\r\n"'"'"'') && \
	export CLOUDFLARE_API_TOKEN="$$CLOUDFLARE_API_TOKEN" && \
	TUNNELS_RESPONSE=$$(curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel" \
		-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
		-H "Content-Type: application/json") && \
	TUNNEL_ID=$$(echo "$$TUNNELS_RESPONSE" | jq -r ".result[] | select(.name==\"$$TUNNEL_NAME\" and .deleted_at==null) | .id" 2>/dev/null | head -1) && \
	if [ -z "$$TUNNEL_ID" ] || [ "$$TUNNEL_ID" = "null" ]; then \
		echo "❌ Tunnel $$TUNNEL_NAME does not exist. Run 'make tunnel-create' first." && \
		exit 1; \
	fi && \
	echo "🌐 Creating DNS records..." && \
	for SUBDOMAIN in ui api argocd; do \
		HOSTNAME="$$CLUSTER_LABEL$$SUBDOMAIN.diocesanvitality.org" && \
		TARGET="$$TUNNEL_ID.cfargotunnel.com" && \
		echo "🔍 Creating DNS record: $$HOSTNAME -> $$TARGET" && \
		DNS_CHECK_RESPONSE=$$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$$ZONE_ID/dns_records?name=$$HOSTNAME" \
			-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN") && \
		echo "📄 DNS check response: $$DNS_CHECK_RESPONSE" && \
		EXISTING=$$(echo "$$DNS_CHECK_RESPONSE" | jq -r '.result[0].id // "null"') && \
		if [ "$$EXISTING" != "null" ]; then \
			echo "🔄 Updating existing DNS record: $$HOSTNAME (ID: $$EXISTING)" && \
			DNS_UPDATE_RESPONSE=$$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$$ZONE_ID/dns_records/$$EXISTING" \
				-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
				-H "Content-Type: application/json" \
				--data "{\"type\":\"CNAME\",\"name\":\"$$HOSTNAME\",\"content\":\"$$TARGET\",\"proxied\":true}") && \
			echo "📄 DNS update response: $$DNS_UPDATE_RESPONSE"; \
		else \
			echo "🆕 Creating new DNS record: $$HOSTNAME" && \
			DNS_CREATE_RESPONSE=$$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$$ZONE_ID/dns_records" \
				-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
				-H "Content-Type: application/json" \
				--data "{\"type\":\"CNAME\",\"name\":\"$$HOSTNAME\",\"content\":\"$$TARGET\",\"proxied\":true}") && \
			echo "📄 DNS create response: $$DNS_CREATE_RESPONSE"; \
		fi && \
		echo "✅ DNS record configured: $$HOSTNAME"; \
	done && \
	echo "🔧 Configuring tunnel public hostnames for SSL certificate generation..." && \
	TUNNEL_CONFIG_RESPONSE=$$(curl -s -X PUT "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel/$$TUNNEL_ID/configurations" \
		-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
		-H "Content-Type: application/json" \
		--data '{ \
			"config": { \
				"ingress": [ \
					{ \
						"hostname": "'"$$CLUSTER_LABEL"'ui.diocesanvitality.org", \
						"service": "http://frontend-service.diocesan-vitality-'"$$CLUSTER_LABEL"'.svc.cluster.local:80" \
					}, \
					{ \
						"hostname": "'"$$CLUSTER_LABEL"'api.diocesanvitality.org", \
						"service": "http://backend-service.diocesan-vitality-'"$$CLUSTER_LABEL"'.svc.cluster.local:8000" \
					}, \
					{ \
						"hostname": "'"$$CLUSTER_LABEL"'argocd.diocesanvitality.org", \
						"service": "http://argocd-server.argocd:80" \
					}, \
					{ \
						"service": "http_status:404" \
					} \
				] \
			} \
		}') && \
	echo "📄 Tunnel configuration response: $$TUNNEL_CONFIG_RESPONSE" && \
	if echo "$$TUNNEL_CONFIG_RESPONSE" | jq -e '.success == true' >/dev/null 2>&1; then \
		echo "✅ Tunnel public hostnames configured - SSL certificates will be automatically generated"; \
	else \
		echo "⚠️  Tunnel configuration may have issues, but continuing..."; \
	fi && \
	echo "📋 Tunnel Information:" && \
	echo "   Tunnel Name: $$TUNNEL_NAME" && \
	echo "   Tunnel ID: $$TUNNEL_ID" && \
	echo "   Public Hostnames:" && \
	echo "     - $${CLUSTER_LABEL}ui.diocesanvitality.org (→ frontend-service.diocesan-vitality-$$CLUSTER_LABEL.svc.cluster.local:80)" && \
	echo "     - $${CLUSTER_LABEL}api.diocesanvitality.org (→ backend-service.diocesan-vitality-$$CLUSTER_LABEL.svc.cluster.local:8000)" && \
	echo "     - $${CLUSTER_LABEL}argocd.diocesanvitality.org (→ argocd-server.argocd:80)" && \
	echo "✅ Step 8 Complete: Tunnel DNS records and SSL certificates configured"

tunnel-dns-destroy: ## Step 8b: Remove tunnel DNS records (usage: make tunnel-dns-destroy CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🗑️  Step 8b: Removing tunnel DNS records for '$$CLUSTER_LABEL'..." && \
	$(MAKE) tunnel-auth && \
	CLOUDFLARE_API_TOKEN=$$(sed -n 's/^CLOUDFLARE_API_TOKEN=//p' .env | tr -d '\r\n"'"'"'') && \
	ZONE_ID=$$(sed -n 's/^CLOUDFLARE_ZONE_ID=//p' .env | tr -d '\r\n"'"'"'') && \
	export CLOUDFLARE_API_TOKEN="$$CLOUDFLARE_API_TOKEN" && \
	DELETED_COUNT=0 && \
	SKIPPED_COUNT=0 && \
	for SUBDOMAIN in ui api argocd; do \
		HOSTNAME="$$CLUSTER_LABEL.$$SUBDOMAIN.diocesanvitality.org" && \
		echo "  🔍 Checking: $$HOSTNAME..." && \
		DNS_CHECK_RESPONSE=$$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$$ZONE_ID/dns_records?name=$$HOSTNAME" \
			-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN") && \
		EXISTING=$$(echo "$$DNS_CHECK_RESPONSE" | jq -r '.result[0].id // "null"') && \
		if [ "$$EXISTING" != "null" ]; then \
			echo "  🗑️  Deleting: $$HOSTNAME (ID: $$EXISTING)" && \
			DNS_DELETE_RESPONSE=$$(curl -s -X DELETE "https://api.cloudflare.com/client/v4/zones/$$ZONE_ID/dns_records/$$EXISTING" \
				-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN") && \
			if echo "$$DNS_DELETE_RESPONSE" | jq -e '.success == true' >/dev/null 2>&1; then \
				echo "  ✅ Deleted: $$HOSTNAME" && \
				DELETED_COUNT=$$((DELETED_COUNT + 1)); \
			else \
				echo "  ⚠️  Warning: Deletion may have failed for $$HOSTNAME"; \
			fi; \
		else \
			echo "  ℹ️  Not found: $$HOSTNAME" && \
			SKIPPED_COUNT=$$((SKIPPED_COUNT + 1)); \
		fi; \
	done && \
	echo "" && \
	echo "📊 DNS Destruction Summary:" && \
	echo "   Deleted: $$DELETED_COUNT records" && \
	echo "   Skipped: $$SKIPPED_COUNT records (already deleted)" && \
	echo "✅ Step 8b Complete: DNS records destroyed for $$CLUSTER_LABEL"


argocd-install: ## Step 9: Install ArgoCD via Helm (usage: make argocd-install CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 9: Installing ArgoCD via Helm for '$$CLUSTER_LABEL'..." && \
	echo "🔧 Switching to cluster context... ($$(date '+%H:%M:%S'))" && \
	if ! kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL; then \
		echo "❌ FAILED: Could not switch to kubectl context do-nyc2-dv-$$CLUSTER_LABEL at $$(date '+%H:%M:%S')" && \
		echo "💡 Check if cluster exists: doctl kubernetes cluster list" && \
		exit 1; \
	fi && \
		echo "🔧 Installing Helm if needed... ($$(date '+%H:%M:%S'))" && \
		if ! $(MAKE) _install-helm; then \
			echo "❌ FAILED: Helm installation failed at $$(date '+%H:%M:%S')" && \
			exit 1; \
		fi && \
		echo "📦 Adding ArgoCD Helm repository... ($$(date '+%H:%M:%S'))" && \
		if ! helm repo add argo https://argoproj.github.io/argo-helm; then \
			echo "❌ FAILED: Could not add ArgoCD Helm repository at $$(date '+%H:%M:%S')" && \
			exit 1; \
		fi && \
		if ! helm repo update; then \
			echo "❌ FAILED: Helm repo update failed at $$(date '+%H:%M:%S')" && \
			exit 1; \
		fi && \
		echo "🏗️  Creating ArgoCD namespace... ($$(date '+%H:%M:%S'))" && \
		if ! kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -; then \
			echo "❌ FAILED: Could not create argocd namespace at $$(date '+%H:%M:%S')" && \
			exit 1; \
		fi && \
		echo "🚀 Installing ArgoCD with values-$$CLUSTER_LABEL.yaml... ($$(date '+%H:%M:%S'))" && \
		if ! helm upgrade --install argocd argo/argo-cd \
			--namespace argocd \
			--values k8s/infrastructure/argocd/values-$$CLUSTER_LABEL.yaml \
			--wait --timeout=10m; then \
			echo "❌ FAILED: ArgoCD Helm installation failed at $$(date '+%H:%M:%S')" && \
			echo "💡 Check Helm values file: k8s/infrastructure/argocd/values-$$CLUSTER_LABEL.yaml" && \
			exit 1; \
		fi && \
		echo "⏳ Waiting for ArgoCD server to be ready... ($$(date '+%H:%M:%S'))" && \
		if ! kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s; then \
			echo "❌ FAILED: ArgoCD server pods not ready within 5 minutes at $$(date '+%H:%M:%S')" && \
			echo "💡 Check pod status: kubectl get pods -n argocd" && \
			exit 1; \
		fi && \
		echo "🔧 Configuring repository access... ($$(date '+%H:%M:%S'))" && \
		TIMEOUT=60 && START_TIME=$$(date +%s) && \
		while ! kubectl get configmap argocd-cm -n argocd >/dev/null 2>&1; do \
			CURRENT_TIME=$$(date +%s) && \
			if [ $$((CURRENT_TIME - START_TIME)) -gt $$TIMEOUT ]; then \
				echo "❌ FAILED: ArgoCD configmap not available within 60 seconds at $$(date '+%H:%M:%S')" && \
				exit 1; \
			fi && \
			sleep 2; \
		done && \
		sleep 5 && \
		if ! kubectl patch configmap argocd-cm -n argocd --patch '{"data":{"repositories":"- url: https://github.com/tomknightatl/diocesan-vitality.git"}}'; then \
			echo "❌ FAILED: Could not configure repository access at $$(date '+%H:%M:%S')" && \
			exit 1; \
		fi
	@echo "🔧 Setting up custom ArgoCD password..."
	@$(MAKE) _setup-argocd-password CLUSTER_LABEL=$$CLUSTER_LABEL
	@echo "🏷️  Registering cluster with ArgoCD..."
	@$(MAKE) _register-cluster-with-argocd CLUSTER_LABEL=$$CLUSTER_LABEL
	@echo "🚀 Deploying root ApplicationSets..."
	@kubectl apply -f k8s/argocd/root-applicationsets-$$CLUSTER_LABEL.yaml
	@echo "✅ Root ApplicationSets deployed - ArgoCD will now manage infrastructure"
	@echo "✅ Step 9 Complete: ArgoCD installed via Helm for $$CLUSTER_LABEL"

_register-cluster-with-argocd: ## Register current cluster with ArgoCD with proper labels
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔗 Registering cluster 'dv-$$CLUSTER_LABEL' with ArgoCD..." && \
	if ! kubectl get secret cluster-info -n default >/dev/null 2>&1; then \
		echo "🏷️  Creating missing cluster-info secret..."; \
		kubectl create secret generic cluster-info \
			--from-literal=environment=$$CLUSTER_LABEL \
			--from-literal=cluster-name=dv-$$CLUSTER_LABEL \
			-n default; \
	fi && \
	kubectl create secret generic argocd-cluster-local -n argocd \
		--from-literal=name=in-cluster \
		--from-literal=server=https://kubernetes.default.svc \
		--from-literal=config='{"tlsClientConfig":{"insecure":true}}' \
		--dry-run=client -o yaml | kubectl apply -f - && \
	kubectl label secret argocd-cluster-local -n argocd \
		argocd.argoproj.io/secret-type=cluster \
		environment=$$CLUSTER_LABEL \
		--overwrite && \
	echo "✅ Cluster registration completed"

_setup-argocd-password: ## Setup custom ArgoCD password from .env using kubectl
	@echo "🔑 Configuring custom ArgoCD password..."
	@INITIAL_PASSWORD=$$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d) && \
	CUSTOM_PASSWORD=$$(grep ARGOCD_ADMIN_PASSWORD_DEV .env 2>/dev/null | cut -d'=' -f2 || echo "") && \
	if [ -z "$$CUSTOM_PASSWORD" ]; then \
		echo "⚠️  ARGOCD_ADMIN_PASSWORD_DEV not found in .env, using initial password"; \
		echo "$$INITIAL_PASSWORD" > .argocd-admin-password; \
		echo "   Initial password saved to: .argocd-admin-password"; \
	else \
		echo "🔄 Setting custom password from .env using kubectl..."; \
		if ! python3 -c "import bcrypt" >/dev/null 2>&1; then \
			echo "📦 Installing bcrypt for password hashing..."; \
			pip3 install bcrypt --break-system-packages >/dev/null 2>&1 || pip3 install bcrypt >/dev/null 2>&1; \
		fi && \
		BCRYPT_HASH=$$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'$$CUSTOM_PASSWORD', bcrypt.gensalt()).decode('utf-8'))") && \
		kubectl patch secret argocd-secret -n argocd --type='merge' -p="{\"data\":{\"admin.password\":\"$$(echo -n "$$BCRYPT_HASH" | base64 -w0)\"}}" && \
		kubectl delete secret argocd-initial-admin-secret -n argocd --ignore-not-found=true && \
		echo "$$CUSTOM_PASSWORD" > .argocd-admin-password && \
		echo "✅ Custom password configured and saved to: .argocd-admin-password"; \
	fi

_deploy-app-of-apps: ## Deploy App-of-Apps root Application for ApplicationSets
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Deploying root Application for ApplicationSets in '$$CLUSTER_LABEL' environment..." && \
	echo "⏳ Waiting for ArgoCD to be fully ready... ($$(date '+%H:%M:%S'))" && \
	sleep 10 && \
	if ! kubectl apply -f k8s/argocd/root-applicationsets-$$CLUSTER_LABEL.yaml; then \
		echo "❌ FAILED: Could not deploy root Application at $$(date '+%H:%M:%S')" && \
		echo "💡 Check file: k8s/argocd/root-applicationsets-$$CLUSTER_LABEL.yaml" && \
		exit 1; \
	fi && \
	echo "⏳ Waiting for root Application to be synced... ($$(date '+%H:%M:%S'))" && \
	TIMEOUT=300 && START_TIME=$$(date +%s) && \
	while ! kubectl get application root-applicationsets-$$CLUSTER_LABEL -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null | grep -q "Synced"; do \
		CURRENT_TIME=$$(date +%s) && \
		if [ $$((CURRENT_TIME - START_TIME)) -gt $$TIMEOUT ]; then \
			echo "❌ FAILED: Root Application not synced within 5 minutes at $$(date '+%H:%M:%S')" && \
			echo "💡 Check Application status: kubectl get application root-applicationsets-$$CLUSTER_LABEL -n argocd" && \
			exit 1; \
		fi && \
		echo "🔄 Waiting for Application sync... ($$((CURRENT_TIME - START_TIME))s elapsed)" && \
		sleep 5; \
	done && \
	echo "✅ Root Application deployed and synced successfully" && \
	echo "🔍 ApplicationSets that will be deployed:" && \
	kubectl get applicationsets -n argocd --no-headers 2>/dev/null | grep "$$CLUSTER_LABEL" | awk '{print "  - " $$1}' || echo "  (ApplicationSets will appear shortly)" && \
	echo "💡 Monitor ApplicationSets: kubectl get applicationsets -n argocd"

sealed-secret: sealed-secrets-create ## Alias for sealed-secrets-create target

argocd-password: ## Get ArgoCD admin password

argocd-apps: ## Deploy ArgoCD App-of-Apps root Application (usage: make argocd-apps CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Deploying ArgoCD App-of-Apps root Application for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	$(MAKE) _deploy-app-of-apps CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "✅ ArgoCD App-of-Apps deployment complete for $$CLUSTER_LABEL"

sealed-secrets-create: ## Step 4: Create sealed secrets for tunnel and application (usage: make sealed-secrets-create CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 4: Creating sealed secrets for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "🔧 Installing kubeseal CLI if needed..." && \
	$(MAKE) _install-kubeseal && \
	echo "⏳ Waiting for sealed-secrets controller to be ready..." && \
	kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=sealed-secrets -n kube-system --timeout=300s && \
	echo "" && \
	echo "🔐 PART 1: Creating tunnel token sealed secret..." && \
	$(MAKE) _create-tunnel-sealed-secret CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "" && \
	echo "🔐 PART 2: Creating application secrets sealed secret..." && \
	$(MAKE) _create-application-sealed-secret CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "" && \
	echo "💾 Committing all sealed secrets to repository..." && \
	$(MAKE) _commit-sealed-secrets CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "" && \
	echo "✅ Step 4 Complete: All sealed secrets created for $$CLUSTER_LABEL"

tunnel-test: ## Step 5: Test Cloudflare tunnel health (usage: make tunnel-test CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔍 Step 5: Testing Cloudflare tunnel health for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "" && \
	echo "🔍 Part 1: Checking sealed secrets status..." && \
	TUNNEL_SECRET_STATUS=$$(kubectl get sealedsecret cloudflared-token -n cloudflare-tunnel-$$CLUSTER_LABEL -o jsonpath='{.status.conditions[0].type}' 2>/dev/null || echo "NotFound") && \
	APP_SECRET_STATUS=$$(kubectl get sealedsecret diocesan-vitality-secrets -n diocesan-vitality-$$CLUSTER_LABEL -o jsonpath='{.status.conditions[0].type}' 2>/dev/null || echo "NotFound") && \
	if [ "$$TUNNEL_SECRET_STATUS" = "NotFound" ]; then \
		echo "❌ Tunnel sealed secret not found in cloudflare-tunnel-$$CLUSTER_LABEL namespace"; \
		exit 1; \
	fi && \
	if [ "$$APP_SECRET_STATUS" = "NotFound" ]; then \
		echo "❌ Application sealed secret not found in diocesan-vitality-$$CLUSTER_LABEL namespace"; \
		exit 1; \
	fi && \
	echo "✅ Sealed secrets exist in cluster" && \
	echo "" && \
	echo "🔍 Part 2: Verifying secrets were decrypted..." && \
	if ! kubectl get secret cloudflared-token -n cloudflare-tunnel-$$CLUSTER_LABEL >/dev/null 2>&1; then \
		echo "❌ Tunnel secret not decrypted (Secret object not found)"; \
		echo "💡 Check sealed-secrets controller logs: kubectl logs -n kube-system deployment/sealed-secrets-controller"; \
		exit 1; \
	fi && \
	if ! kubectl get secret diocesan-vitality-secrets -n diocesan-vitality-$$CLUSTER_LABEL >/dev/null 2>&1; then \
		echo "❌ Application secrets not decrypted (Secret object not found)"; \
		echo "💡 Check sealed-secrets controller logs: kubectl logs -n kube-system deployment/sealed-secrets-controller"; \
		exit 1; \
	fi && \
	echo "✅ Secrets successfully decrypted by sealed-secrets controller" && \
	echo "" && \
	echo "🔍 Part 3: Checking tunnel pod status..." && \
	if ! kubectl get pods -n cloudflare-tunnel-$$CLUSTER_LABEL -l app=cloudflared >/dev/null 2>&1; then \
		echo "❌ No tunnel pods found"; \
		echo "💡 Check ApplicationSet: kubectl get applicationset cloudflare-tunnel-$$CLUSTER_LABEL-applicationset -n argocd"; \
		exit 1; \
	fi && \
	TUNNEL_POD_STATUS=$$(kubectl get pods -n cloudflare-tunnel-$$CLUSTER_LABEL -l app=cloudflared -o jsonpath='{.items[0].status.phase}' 2>/dev/null) && \
	TUNNEL_POD_READY=$$(kubectl get pods -n cloudflare-tunnel-$$CLUSTER_LABEL -l app=cloudflared -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null) && \
	if [ "$$TUNNEL_POD_STATUS" != "Running" ] || [ "$$TUNNEL_POD_READY" != "true" ]; then \
		echo "❌ Tunnel pod not healthy (Status: $$TUNNEL_POD_STATUS, Ready: $$TUNNEL_POD_READY)"; \
		echo "💡 Check pod logs: kubectl logs -n cloudflare-tunnel-$$CLUSTER_LABEL -l app=cloudflared"; \
		exit 1; \
	fi && \
	echo "✅ Tunnel pod is Running and Ready" && \
	echo "" && \
	echo "🔍 Part 4: Verifying tunnel connectivity..." && \
	TUNNEL_LOGS=$$(kubectl logs -n cloudflare-tunnel-$$CLUSTER_LABEL -l app=cloudflared --tail=50 2>/dev/null) && \
	if echo "$$TUNNEL_LOGS" | grep -q "Connection.*registered"; then \
		echo "✅ Tunnel successfully registered with Cloudflare edge"; \
	elif echo "$$TUNNEL_LOGS" | grep -q "error.*authentication\|error.*token"; then \
		echo "❌ Tunnel authentication error detected"; \
		echo "💡 Check tunnel token: make tunnel-verify CLUSTER_LABEL=$$CLUSTER_LABEL"; \
		exit 1; \
	else \
		echo "⚠️  Unable to confirm tunnel registration (logs may be insufficient)"; \
	fi && \
	echo "" && \
	echo "✅ Step 5 Complete: Tunnel health check passed for $$CLUSTER_LABEL" && \
	echo "" && \
	echo "📊 Tunnel Status Summary:" && \
	echo "   Tunnel Pod: $$(kubectl get pods -n cloudflare-tunnel-$$CLUSTER_LABEL -l app=cloudflared -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)" && \
	echo "   Status: $$TUNNEL_POD_STATUS" && \
	echo "   Ready: $$TUNNEL_POD_READY" && \
	echo "" && \
	echo "🌐 Expected URLs:" && \
	echo "   Frontend: https://$${CLUSTER_LABEL}ui.diocesanvitality.org" && \
	echo "   Backend:  https://$${CLUSTER_LABEL}api.diocesanvitality.org" && \
	echo "   ArgoCD:   https://$${CLUSTER_LABEL}argocd.diocesanvitality.org"

_create-tunnel-sealed-secret: ## Create tunnel token sealed secret
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔍 Loading tunnel token from environment file..." && \
	if [ ! -f ".tunnel-token-$$CLUSTER_LABEL" ]; then \
		echo "❌ Could not find tunnel token file: .tunnel-token-$$CLUSTER_LABEL"; \
		echo "💡 Ensure tunnel verification has been run: make tunnel-verify CLUSTER_LABEL=$$CLUSTER_LABEL"; \
		exit 1; \
	fi && \
	TUNNEL_TOKEN=$$(grep "TUNNEL_TOKEN_$$CLUSTER_LABEL" .tunnel-token-$$CLUSTER_LABEL | cut -d'=' -f2-) && \
	if [ -z "$$TUNNEL_TOKEN" ]; then \
		echo "❌ Could not extract tunnel token from environment file"; \
		echo "💡 Ensure tunnel verification has been run: make tunnel-verify CLUSTER_LABEL=$$CLUSTER_LABEL"; \
		exit 1; \
	fi && \
	echo "✅ Loaded tunnel token from environment file" && \
	echo "🔍 Extracting tunnel ID for logging..." && \
	TUNNEL_INFO=$$(echo "$$TUNNEL_TOKEN" | base64 -d) && \
	TUNNEL_ID=$$(echo "$$TUNNEL_INFO" | jq -r '.t // "unknown"') && \
	echo "✅ Tunnel ID: $$TUNNEL_ID" && \
	echo "🔐 Creating sealed secret from tunnel token..." && \
	echo -n "$$TUNNEL_TOKEN" | kubectl create secret generic cloudflared-token \
		--dry-run=client --from-file=tunnel-token=/dev/stdin \
		--namespace=cloudflare-tunnel-$$CLUSTER_LABEL -o yaml | \
	kubeseal --controller-namespace=kube-system --controller-name=sealed-secrets-controller \
		-o yaml --namespace=cloudflare-tunnel-$$CLUSTER_LABEL > \
		k8s/infrastructure/cloudflare-tunnel/environments/$$CLUSTER_LABEL/cloudflared-token-sealedsecret.yaml && \
	echo "🔧 Updating kustomization to include sealed secret..." && \
	$(MAKE) _update-kustomization-for-sealed-secret CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "✅ Tunnel sealed secret created: $$TUNNEL_ID"

_create-application-sealed-secret: ## Create application secrets sealed secret
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔍 Loading application secrets from .env file..." && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found. Please copy .env.example to .env and configure your secrets"; \
		exit 1; \
	fi && \
	SUPABASE_URL_VAR="SUPABASE_URL" && \
	SUPABASE_KEY_VAR="SUPABASE_KEY" && \
	if [ "$$CLUSTER_LABEL" != "prd" ]; then \
		ENV_SUFFIX=$$(echo $$CLUSTER_LABEL | tr '[:lower:]' '[:upper:]') && \
		SUPABASE_URL_ENV=$$(grep "^SUPABASE_URL_$$ENV_SUFFIX=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' | sed 's/^[[:space:]]*//;s/[[:space:]]*$$//') && \
		SUPABASE_KEY_ENV=$$(grep "^SUPABASE_KEY_$$ENV_SUFFIX=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' | sed 's/^[[:space:]]*//;s/[[:space:]]*$$//') && \
		if [ -n "$$SUPABASE_URL_ENV" ] && [ -n "$$SUPABASE_KEY_ENV" ] && \
		   ! echo "$$SUPABASE_URL_ENV" | grep -qE '^<.*>$$|^your-|^replace-|^placeholder' && \
		   ! echo "$$SUPABASE_KEY_ENV" | grep -qE '^<.*>$$|^your-|^replace-|^placeholder'; then \
			echo "ℹ️  Using environment-specific database credentials (SUPABASE_URL_$$ENV_SUFFIX, SUPABASE_KEY_$$ENV_SUFFIX)"; \
			SUPABASE_URL="$$SUPABASE_URL_ENV" && \
			SUPABASE_KEY="$$SUPABASE_KEY_ENV"; \
		else \
			echo "⚠️  No environment-specific credentials found, falling back to production database"; \
			echo "💡 To use isolated $$CLUSTER_LABEL database, run: make database-create CLUSTER_LABEL=$$CLUSTER_LABEL"; \
			SUPABASE_URL=$$(grep "^SUPABASE_URL=" .env | cut -d'=' -f2- | tr -d '"') && \
			SUPABASE_KEY=$$(grep "^SUPABASE_KEY=" .env | cut -d'=' -f2- | tr -d '"'); \
		fi; \
	else \
		SUPABASE_URL=$$(grep "^SUPABASE_URL=" .env | cut -d'=' -f2- | tr -d '"') && \
		SUPABASE_KEY=$$(grep "^SUPABASE_KEY=" .env | cut -d'=' -f2- | tr -d '"'); \
	fi && \
	GENAI_API_KEY=$$(grep "^GENAI_API_KEY=" .env | cut -d'=' -f2- | tr -d '"') && \
	SEARCH_API_KEY=$$(grep "^SEARCH_API_KEY=" .env | cut -d'=' -f2- | tr -d '"') && \
	SEARCH_CX=$$(grep "^SEARCH_CX=" .env | cut -d'=' -f2- | tr -d '"') && \
	if [ -z "$$SUPABASE_URL" ] || [ -z "$$SUPABASE_KEY" ] || [ -z "$$GENAI_API_KEY" ] || [ -z "$$SEARCH_API_KEY" ] || [ -z "$$SEARCH_CX" ]; then \
		echo "❌ Missing required secrets in .env file. Required:"; \
		echo "   SUPABASE_URL, SUPABASE_KEY (or SUPABASE_URL_$$ENV_SUFFIX, SUPABASE_KEY_$$ENV_SUFFIX)"; \
		echo "   GENAI_API_KEY, SEARCH_API_KEY, SEARCH_CX"; \
		exit 1; \
	fi && \
	echo "✅ Loaded application secrets from .env file" && \
	echo "   Database: $$SUPABASE_URL" && \
	echo "🔐 Creating sealed secret for application..." && \
	kubectl create secret generic diocesan-vitality-secrets \
		--from-literal=supabase-url="$$SUPABASE_URL" \
		--from-literal=supabase-key="$$SUPABASE_KEY" \
		--from-literal=genai-api-key="$$GENAI_API_KEY" \
		--from-literal=search-api-key="$$SEARCH_API_KEY" \
		--from-literal=search-cx="$$SEARCH_CX" \
		--namespace=diocesan-vitality-$$CLUSTER_LABEL \
		--dry-run=client -o yaml | \
	kubeseal --controller-namespace=kube-system --controller-name=sealed-secrets-controller \
		-o yaml --namespace=diocesan-vitality-$$CLUSTER_LABEL > \
		k8s/environments/$$CLUSTER_LABEL/diocesan-vitality-secrets-sealedsecret.yaml && \
	echo "🔧 Adding sealed secret to kustomization..." && \
	if ! grep -q "diocesan-vitality-secrets-sealedsecret.yaml" k8s/environments/$$CLUSTER_LABEL/kustomization.yaml; then \
		sed -i '/- namespace.yaml/a\  - diocesan-vitality-secrets-sealedsecret.yaml' k8s/environments/$$CLUSTER_LABEL/kustomization.yaml; \
	fi && \
	echo "💾 Committing application sealed secret to repository..." && \
	git add k8s/environments/$$CLUSTER_LABEL/ && \
	PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "Add application sealed secret for diocesan-vitality-$$CLUSTER_LABEL [skip ci]" -m "Contains encrypted supabase-url, supabase-key, genai-api-key, search-api-key, search-cx" && \
	git pull --rebase && \
	git push && \
	echo "✅ Application sealed secret created and committed"

_commit-sealed-secrets: ## Commit all sealed secrets to repository
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "📝 Staging all sealed secret files..." && \
	git add k8s/infrastructure/cloudflare-tunnel/environments/$$CLUSTER_LABEL/ || true && \
	git add k8s/environments/$$CLUSTER_LABEL/ && \
	echo "💾 Committing sealed secrets to repository..." && \
	PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "🔐 Add sealed secrets for $$CLUSTER_LABEL environment [skip ci]" \
		-m "✅ Tunnel Secret:" \
		-m "- cloudflared-token: Encrypted tunnel token for Cloudflare tunnel" \
		-m "" \
		-m "✅ Application Secrets:" \
		-m "- supabase-url: Database connection URL" \
		-m "- supabase-key: Database API key" \
		-m "- genai-api-key: Google Gemini AI API key" \
		-m "- search-api-key: Google Custom Search API key" \
		-m "- search-cx: Google Custom Search CX ID" \
		-m "" \
		-m "🔒 All secrets encrypted with cluster-specific sealed-secrets key" \
		-m "🚀 ArgoCD will auto-deploy when synced from GitOps repository" && \
	git pull --rebase && \
	git push && \
	echo "✅ All sealed secrets committed and pushed to repository"

_cleanup-sealed-secrets: ## Delete sealed secrets from repository after cluster destroy
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🧹 Cleaning up sealed secrets for $$CLUSTER_LABEL environment..." && \
	TUNNEL_SECRET="k8s/infrastructure/cloudflare-tunnel/environments/$$CLUSTER_LABEL/cloudflared-token-sealedsecret.yaml" && \
	APP_SECRET="k8s/environments/$$CLUSTER_LABEL/diocesan-vitality-secrets-sealedsecret.yaml" && \
	if [ -f "$$TUNNEL_SECRET" ]; then \
		echo "🗑️  Removing tunnel sealed secret: $$TUNNEL_SECRET" && \
		git rm "$$TUNNEL_SECRET" || rm -f "$$TUNNEL_SECRET"; \
	fi && \
	if [ -f "$$APP_SECRET" ]; then \
		echo "🗑️  Removing application sealed secret: $$APP_SECRET" && \
		git rm "$$APP_SECRET" || rm -f "$$APP_SECRET"; \
	fi && \
	if git diff --cached --quiet; then \
		echo "ℹ️  No sealed secrets to clean up"; \
	else \
		echo "💾 Committing sealed secret cleanup..." && \
		PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "🧹 Remove sealed secrets for $$CLUSTER_LABEL after cluster destroy [skip ci]" \
			-m "These sealed secrets were encrypted with the old cluster's certificate" \
			-m "and cannot be decrypted by a new cluster's sealed-secrets controller." \
			-m "" \
			-m "Run 'make sealed-secrets-create CLUSTER_LABEL=$$CLUSTER_LABEL' to regenerate" && \
		git pull --rebase && \
		git push && \
		echo "✅ Sealed secrets cleaned up and changes pushed"; \
	fi

# Database Management
# ===================

# Phase 4.1 Database Commands
# ============================

db-reset: ## Reset local database from production
	@echo "🔄 Resetting local database from production..."
	@echo "⚠️  WARNING: This will DELETE ALL DATA in your local database!"
	@echo ""
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@read -p "Continue? Type 'yes' to proceed: " CONFIRM </dev/tty && \
	if [ "$$CONFIRM" != "yes" ]; then \
		echo "❌ Operation cancelled"; \
		exit 1; \
	fi
	@echo "🔧 Running database reset script..."
	@python scripts/reset_local_database.py
	@echo "✅ Local database reset complete"

db-migrate: ## Apply local schema changes
	@echo "🔄 Applying local schema changes..."
	@echo "📋 This will apply pending schema migrations to your local database"
	@echo ""
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@echo "🔧 Running schema migration script..."
	@python scripts/apply_schema_change.py --auto
	@echo "✅ Schema changes applied successfully"

db-deploy: ## Deploy to production (requires confirmation)
	@echo "🚀 Deploying to production..."
	@echo "⚠️  WARNING: This will apply schema changes to PRODUCTION!"
	@echo ""
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@echo "📋 Pre-deployment checks:"
	@echo "   - Testing migrations locally first..."
	@python scripts/test_migration.py --all-pending || { \
		echo "❌ Migration tests failed! Aborting deployment."; \
		exit 1; \
	}
	@echo "✅ Migration tests passed"
	@echo ""
	@read -p "Deploy to PRODUCTION? Type 'yes' to proceed: " CONFIRM </dev/tty && \
	if [ "$$CONFIRM" != "yes" ]; then \
		echo "❌ Operation cancelled"; \
		exit 1; \
	fi
	@echo "🔧 Running production deployment script..."
	@python scripts/deploy_to_production.py --auto
	@echo "✅ Production deployment complete"

db-backup: ## Create production database backup
	@echo "💾 Creating production database backup..."
	@echo "📋 This will create a timestamped backup of the production database"
	@echo ""
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@echo "🔧 Running backup script..."
	@python scripts/backup_production_database.py
	@echo "✅ Production database backup complete"

db-test: ## Test migrations
	@echo "🧪 Testing migrations..."
	@echo "📋 This will test all pending migrations without applying them"
	@echo ""
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@echo "🔧 Running migration test script..."
	@python scripts/test_migration.py --all-pending
	@echo "✅ Migration tests complete"

db-status: ## Check database status and pending migrations
	@echo "🔍 Checking database status..."
	@echo ""
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@echo "📊 Database Connection Status:"
	@python scripts/dev_test.py --db
	@echo ""
	@echo "📋 Pending Migrations:"
	@python scripts/test_migration.py --list-pending || echo "  No pending migrations or unable to list"
	@echo ""
	@echo "✅ Database status check complete"

db-validate: ## Validate migrations before deployment
	@echo "✅ Validating migrations before deployment..."
	@echo ""
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@echo "🔧 Running comprehensive validation..."
	@echo "   Step 1/3: Checking database connection..."
	@python scripts/dev_test.py --db || { \
		echo "❌ Database connection failed!"; \
		exit 1; \
	}
	@echo "   ✅ Database connection OK"
	@echo "   Step 2/3: Testing migration scripts..."
	@python scripts/test_migration.py --all-pending || { \
		echo "❌ Migration tests failed!"; \
		exit 1; \
	}
	@echo "   ✅ Migration tests passed"
	@echo "   Step 3/3: Validating schema syntax..."
	@python scripts/apply_schema_change.py --validate-only || { \
		echo "❌ Schema validation failed!"; \
		exit 1; \
	}
	@echo "   ✅ Schema validation passed"
	@echo ""
	@echo "✅ All validations passed - ready for deployment"

db-rollback: ## Emergency rollback of last migration
	@echo "🚨 EMERGENCY ROLLBACK - Reverting last migration..."
	@echo "⚠️  WARNING: This is a destructive operation!"
	@echo ""
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@read -p "Rollback last migration? Type 'yes' to proceed: " CONFIRM </dev/tty && \
	if [ "$$CONFIRM" != "yes" ]; then \
		echo "❌ Operation cancelled"; \
		exit 1; \
	fi
	@echo "🔧 Running rollback script..."
	@python scripts/apply_schema_change.py --rollback
	@echo "✅ Rollback complete"

db-dev: ## Quick local development database setup
	@echo "🚀 Setting up local development database..."
	@echo ""
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@echo "📋 Development setup steps:"
	@echo "   Step 1/3: Checking environment..."
	@python scripts/dev_test.py --env || { \
		echo "❌ Environment check failed!"; \
		exit 1; \
	}
	@echo "   ✅ Environment OK"
	@echo "   Step 2/3: Testing database connection..."
	@python scripts/dev_test.py --db || { \
		echo "❌ Database connection failed!"; \
		exit 1; \
	}
	@echo "   ✅ Database connection OK"
	@echo "   Step 3/3: Checking for pending migrations..."
	@python scripts/test_migration.py --list-pending || echo "   ℹ️  No pending migrations"
	@echo ""
	@echo "✅ Local development database ready!"
	@echo "💡 Use 'make db-migrate' to apply pending migrations"

# Database Aliases and Shortcuts
# ===============================

reset: db-reset ## Alias for db-reset
migrate: db-migrate ## Alias for db-migrate
deploy: db-deploy ## Alias for db-deploy
backup: db-backup ## Alias for db-backup
test-db: db-test ## Alias for db-test
status: db-status ## Alias for db-status
validate: db-validate ## Alias for db-validate
rollback: db-rollback ## Alias for db-rollback
dev-db: db-dev ## Alias for db-dev

# Legacy Database Commands
# ========================

database-create: ## Copy production database to environment-specific database (usage: make database-create CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🗄️  Database copy for '$$CLUSTER_LABEL' environment..." && \
	echo "" && \
	if [ "$$CLUSTER_LABEL" = "prd" ]; then \
		echo "ℹ️  Production is the source database - no copy needed"; \
		exit 0; \
	fi && \
	echo "🔍 Checking environment-specific database credentials..." && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi && \
	ENV_SUFFIX=$$(echo $$CLUSTER_LABEL | tr '[:lower:]' '[:upper:]') && \
	SUPABASE_URL_DEV=$$(grep "^SUPABASE_URL_$$ENV_SUFFIX=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"') && \
	SUPABASE_KEY_DEV=$$(grep "^SUPABASE_KEY_$$ENV_SUFFIX=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"') && \
	SUPABASE_DB_PASSWORD_DEV=$$(grep "^SUPABASE_DB_PASSWORD_$$ENV_SUFFIX=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"') && \
	SUPABASE_URL_PRD=$$(grep "^SUPABASE_URL=" .env | cut -d'=' -f2- | tr -d '"') && \
	SUPABASE_KEY_PRD=$$(grep "^SUPABASE_KEY=" .env | cut -d'=' -f2- | tr -d '"') && \
	SUPABASE_DB_PASSWORD_PRD=$$(grep "^SUPABASE_DB_PASSWORD=" .env | cut -d'=' -f2- | tr -d '"') && \
	if [ -z "$$SUPABASE_URL_DEV" ] || [ -z "$$SUPABASE_KEY_DEV" ]; then \
		echo "❌ Missing $$CLUSTER_LABEL database credentials in .env"; \
		echo "" && \
		echo "📋 Prerequisites:" && \
		echo "1. Manually create Supabase project: diocesan-vitality-$$CLUSTER_LABEL" && \
		echo "2. Add credentials to .env:" && \
		echo "   SUPABASE_URL_$$ENV_SUFFIX=<your-dev-url>" && \
		echo "   SUPABASE_KEY_$$ENV_SUFFIX=<your-dev-key>" && \
		echo "3. Run this command again" && \
		exit 1; \
	fi && \
	echo "✅ Found $$CLUSTER_LABEL database credentials" && \
	echo "" && \
	echo "📊 Database Copy Operation:" && \
	echo "   Source: $$SUPABASE_URL_PRD" && \
	echo "   Target: $$SUPABASE_URL_DEV" && \
	echo "" && \
	echo "⚠️  This will:" && \
	echo "   - Export schema and data from production" && \
	echo "   - Drop existing tables in $$CLUSTER_LABEL database" && \
	echo "   - Import production data into $$CLUSTER_LABEL database" && \
	echo "" && \
	if [ -z "$$SKIP_CONFIRM" ]; then \
		read -p "Continue? Type 'yes' to proceed: " CONFIRM </dev/tty && \
		if [ "$$CONFIRM" != "yes" ]; then \
			echo "❌ Operation cancelled"; \
			exit 1; \
		fi; \
	else \
		echo "ℹ️  Auto-confirming (SKIP_CONFIRM=1)"; \
	fi && \
	echo "" && \
	echo "🔄 Copying production database to $$CLUSTER_LABEL..." && \
	$(MAKE) _database-copy-internal SUPABASE_URL_SRC="$$SUPABASE_URL_PRD" SUPABASE_KEY_SRC="$$SUPABASE_KEY_PRD" SUPABASE_DB_PASSWORD_SRC="$$SUPABASE_DB_PASSWORD_PRD" SUPABASE_URL_DST="$$SUPABASE_URL_DEV" SUPABASE_KEY_DST="$$SUPABASE_KEY_DEV" SUPABASE_DB_PASSWORD_DST="$$SUPABASE_DB_PASSWORD_DEV" CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "" && \
	echo "✅ Database copy complete for $$CLUSTER_LABEL" && \
	echo "" && \
	echo "Next steps:" && \
	echo "   make sealed-secrets-create CLUSTER_LABEL=$$CLUSTER_LABEL"

_database-copy-internal: ## Internal target to perform database copy using pg_dump/pg_restore
	@echo "🔧 Installing dependencies..." && \
	if ! command -v psql >/dev/null 2>&1; then \
		echo "📦 Installing postgresql-client..." && \
		sudo apt-get update -qq && sudo apt-get install -y postgresql-client; \
	fi && \
	echo "✅ Dependencies ready" && \
	echo "" && \
	echo "🔍 Extracting database connection details..." && \
	SRC_HOST=$$(echo $(SUPABASE_URL_SRC) | sed 's|https://||' | sed 's|http://||' | cut -d'/' -f1) && \
	SRC_PROJECT=$$(echo $$SRC_HOST | cut -d'.' -f1) && \
	DST_HOST=$$(echo $(SUPABASE_URL_DST) | sed 's|https://||' | sed 's|http://||' | cut -d'/' -f1) && \
	DST_PROJECT=$$(echo $$DST_HOST | cut -d'.' -f1) && \
	echo "   Source project: $$SRC_PROJECT" && \
	echo "   Target project: $$DST_PROJECT" && \
	echo "" && \
	if [ -z "$(SUPABASE_DB_PASSWORD_SRC)" ] || [ -z "$(SUPABASE_DB_PASSWORD_DST)" ]; then \
		echo "⚠️  Missing database passwords in .env" && \
		echo "💡 Add SUPABASE_DB_PASSWORD and SUPABASE_DB_PASSWORD_DEV to .env" && \
		exit 1; \
	fi && \
	echo "⚠️  Manual database copy required (IPv6 connectivity needed for direct access)" && \
	echo "" && \
	echo "📋 Option 1: Use Supabase Dashboard (Easiest - works on free tier)" && \
	echo "   1. Export: Open https://supabase.com/dashboard/project/$$SRC_PROJECT/editor" && \
	echo "      Run SQL: SELECT * FROM dioceses; -- Copy all table data" && \
	echo "   2. Import: Open https://supabase.com/dashboard/project/$$DST_PROJECT/editor" && \
	echo "      Paste and run the same queries" && \
	echo "" && \
	echo "📋 Option 2: Use pg_dump from machine with IPv6" && \
	echo "   From a machine with IPv6 connectivity, run:" && \
	echo "   PGPASSWORD='$(SUPABASE_DB_PASSWORD_SRC)' pg_dump -h db.$$SRC_PROJECT.supabase.co -U postgres -d postgres > backup.sql" && \
	echo "   PGPASSWORD='$(SUPABASE_DB_PASSWORD_DST)' psql -h db.$$DST_PROJECT.supabase.co -U postgres -d postgres < backup.sql" && \
	echo "" && \
	echo "💡 For now, dev can share production database (already configured)" && \
	echo "   Environment-specific credentials will be used when database is populated"

database-copy-prd-to-dev: ## Copy production database to dev using Python script (usage: make database-copy-prd-to-dev)
	@echo "🔄 Copying production database to dev..." && \
	echo "" && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi && \
	export SUPABASE_URL_PRD=$$(grep "^SUPABASE_URL=" .env | cut -d'=' -f2- | tr -d '"') && \
	export SUPABASE_KEY_PRD=$$(grep "^SUPABASE_KEY=" .env | cut -d'=' -f2- | tr -d '"') && \
	export SUPABASE_URL_DEV=$$(grep "^SUPABASE_URL_DEV=" .env | cut -d'=' -f2- | tr -d '"') && \
	export SUPABASE_KEY_DEV=$$(grep "^SUPABASE_KEY_DEV=" .env | cut -d'=' -f2- | tr -d '"') && \
	if [ -z "$$SUPABASE_URL_DEV" ] || [ -z "$$SUPABASE_KEY_DEV" ]; then \
		echo "❌ Missing dev database credentials in .env"; \
		exit 1; \
	fi && \
	echo "📊 Database Copy Operation:" && \
	echo "   Source: $$SUPABASE_URL_PRD" && \
	echo "   Target: $$SUPABASE_URL_DEV" && \
	echo "" && \
	python3 scripts/copy_database.py

database-schema-refresh: ## Extract current production schema to sql/initial_schema.sql (usage: make database-schema-refresh)
	@echo "🔄 Extracting schema from production database..." && \
	echo "" && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi && \
	SUPABASE_DB_PASSWORD=$$(grep "^SUPABASE_DB_PASSWORD=" .env | cut -d'=' -f2- | tr -d '"') && \
	echo "   Host: aws-0-us-east-2.pooler.supabase.com:5432 (production pooler)" && \
	echo "   Using PostgreSQL 17 client via connection pooler" && \
	echo "" && \
	if [ -f sql/initial_schema.sql ]; then \
		cp sql/initial_schema.sql sql/initial_schema.sql.backup && \
		echo "💾 Backed up existing schema to sql/initial_schema.sql.backup"; \
	fi && \
	PGPASSWORD="$$SUPABASE_DB_PASSWORD" pg_dump \
		-h aws-0-us-east-2.pooler.supabase.com \
		-p 5432 \
		-U postgres.nzcwtjloonumxpsqzarq \
		-d postgres \
		--schema-only \
		--no-owner \
		--no-acl \
		--schema=public \
		-f sql/initial_schema.sql && \
	echo "" && \
	echo "✅ Schema exported successfully to sql/initial_schema.sql" && \
	echo "   Lines: $$(wc -l < sql/initial_schema.sql)" && \
	echo "" && \
	echo "📊 Tables extracted:" && \
	grep -i "CREATE TABLE" sql/initial_schema.sql | sed 's/CREATE TABLE public\./  - /' | sed 's/ (.*$$//'

database-init-dev: ## Initialize dev database with production schema and data (usage: make database-init-dev)
	@echo "🚀 Initializing dev database from production..." && \
	echo "" && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi && \
	SUPABASE_DB_PASSWORD_DEV=$$(grep "^SUPABASE_DB_PASSWORD_DEV=" .env | cut -d'=' -f2- | tr -d '"') && \
	echo "⚠️  WARNING: This will DELETE ALL DATA in dev database!" && \
	echo "" && \
	echo "Step 1/4: Dropping existing dev schema..." && \
	PGPASSWORD="$$SUPABASE_DB_PASSWORD_DEV" psql \
		-h aws-1-us-east-2.pooler.supabase.com \
		-p 5432 \
		-U postgres.derftxlibiidgcdafxrx \
		-d postgres \
		-c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" > /dev/null 2>&1 && \
	echo "✅ Dev schema dropped and recreated" && \
	echo "" && \
	echo "Step 2/4: Applying production schema to dev..." && \
	PGPASSWORD="$$SUPABASE_DB_PASSWORD_DEV" psql \
		-h aws-1-us-east-2.pooler.supabase.com \
		-p 5432 \
		-U postgres.derftxlibiidgcdafxrx \
		-d postgres \
		-f sql/initial_schema.sql > /dev/null 2>&1 && \
	echo "✅ Schema applied to dev" && \
	echo "" && \
	echo "Step 3/4: Granting permissions..." && \
	PGPASSWORD="$$SUPABASE_DB_PASSWORD_DEV" psql \
		-h aws-1-us-east-2.pooler.supabase.com \
		-p 5432 \
		-U postgres.derftxlibiidgcdafxrx \
		-d postgres \
		-c "GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role; \
		    GRANT ALL ON SCHEMA public TO anon, authenticated, service_role; \
		    GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role; \
		    GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role; \
		    GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO anon, authenticated, service_role; \
		    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated, service_role; \
		    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated, service_role; \
		    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon, authenticated, service_role;" > /dev/null 2>&1 && \
	echo "✅ Permissions granted" && \
	echo "" && \
	echo "Step 4/4: Copying production data to dev..." && \
	python3 scripts/copy_database.py && \
	echo "" && \
	echo "🎉 Dev database initialized successfully!"

database-schema-export: ## Export production database schema to SQL file (usage: make database-schema-export)
	@echo "📤 Exporting production database schema..." && \
	echo "" && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi && \
	SUPABASE_URL_PRD=$$(grep "^SUPABASE_URL=" .env | cut -d'=' -f2- | tr -d '"') && \
	SUPABASE_DB_PASSWORD_PRD=$$(grep "^SUPABASE_DB_PASSWORD=" .env | cut -d'=' -f2- | tr -d '"') && \
	if [ -z "$$SUPABASE_URL_PRD" ] || [ -z "$$SUPABASE_DB_PASSWORD_PRD" ]; then \
		echo "❌ Missing production database credentials in .env"; \
		exit 1; \
	fi && \
	SRC_HOST=$$(echo $$SUPABASE_URL_PRD | sed 's|https://||' | sed 's|http://||' | cut -d'/' -f1) && \
	SRC_PROJECT=$$(echo $$SRC_HOST | cut -d'.' -f1) && \
	echo "📊 Schema Export:" && \
	echo "   Source: $$SUPABASE_URL_PRD ($$SRC_PROJECT)" && \
	echo "   Output: sql/exported_schema.sql" && \
	echo "" && \
	echo "⚠️  Note: Requires IPv6 connectivity to Supabase" && \
	echo "🔧 Exporting schema (structure only, no data)..." && \
	PGPASSWORD="$$SUPABASE_DB_PASSWORD_PRD" pg_dump -h db.$$SRC_PROJECT.supabase.co -U postgres -d postgres --schema-only > sql/exported_schema.sql && \
	echo "" && \
	echo "✅ Schema exported successfully!" && \
	echo "💡 Now run: make database-schema-import"

database-schema-import: ## Import schema from exported SQL file to dev database (usage: make database-schema-import)
	@echo "📥 Importing schema to dev database..." && \
	echo "" && \
	if [ ! -f "sql/exported_schema.sql" ]; then \
		echo "❌ Schema file not found: sql/exported_schema.sql"; \
		echo "💡 Run: make database-schema-export first"; \
		exit 1; \
	fi && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi && \
	SUPABASE_URL_DEV=$$(grep "^SUPABASE_URL_DEV=" .env | cut -d'=' -f2- | tr -d '"') && \
	SUPABASE_DB_PASSWORD_DEV=$$(grep "^SUPABASE_DB_PASSWORD_DEV=" .env | cut -d'=' -f2- | tr -d '"') && \
	if [ -z "$$SUPABASE_URL_DEV" ] || [ -z "$$SUPABASE_DB_PASSWORD_DEV" ]; then \
		echo "❌ Missing dev database credentials in .env"; \
		exit 1; \
	fi && \
	DST_HOST=$$(echo $$SUPABASE_URL_DEV | sed 's|https://||' | sed 's|http://||' | cut -d'/' -f1) && \
	DST_PROJECT=$$(echo $$DST_HOST | cut -d'.' -f1) && \
	echo "📊 Schema Import:" && \
	echo "   Target: $$SUPABASE_URL_DEV ($$DST_PROJECT)" && \
	echo "   Source: sql/exported_schema.sql" && \
	echo "" && \
	echo "⚠️  Note: Requires IPv6 connectivity to Supabase" && \
	echo "🔧 Importing schema..." && \
	PGPASSWORD="$$SUPABASE_DB_PASSWORD_DEV" psql -h db.$$DST_PROJECT.supabase.co -U postgres -d postgres -f sql/exported_schema.sql && \
	echo "" && \
	echo "✅ Schema imported successfully!" && \
	echo "💡 Now you can run: make database-copy-prd-to-dev"

database-init: ## Initialize database schema for dev environment using SQL files (usage: make database-init)
	@echo "🗄️  Initializing dev database schema from SQL files..." && \
	echo "" && \
	echo "⚠️  Note: This command requires IPv6 connectivity" && \
	echo "💡 Alternative: Copy sql/initial_schema.sql content to Supabase dashboard SQL editor" && \
	echo "" && \
	echo "📋 Manual steps:" && \
	echo "1. Open: https://supabase.com/dashboard/project/$$(grep "^SUPABASE_URL_DEV=" .env | cut -d'=' -f2- | tr -d '"' | sed 's|https://||' | cut -d'.' -f1)/sql/new" && \
	echo "2. Copy contents of sql/initial_schema.sql" && \
	echo "3. Paste and click 'Run'" && \
	echo "4. Repeat for each file in sql/migrations/ (in alphabetical order)"

database-destroy: ## Display instructions to destroy database project (usage: make database-destroy CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🗑️  Database cleanup for '$$CLUSTER_LABEL' environment..." && \
	echo "" && \
	if [ "$$CLUSTER_LABEL" = "prd" ]; then \
		echo "⚠️  Cannot destroy production database - manual action required"; \
		echo "💡 Production database should never be automatically destroyed"; \
		exit 1; \
	fi && \
	echo "⚠️  Manual steps to destroy $$CLUSTER_LABEL database:" && \
	echo "" && \
	echo "1️⃣  Delete Supabase project:" && \
	echo "   - Go to https://app.supabase.com/" && \
	echo "   - Select project: diocesan-vitality-$$CLUSTER_LABEL" && \
	echo "   - Settings → General → Delete Project" && \
	echo "" && \
	echo "2️⃣  Optionally remove credentials from .env (manual cleanup):" && \
	echo "   You may want to remove or comment out these lines in .env:" && \
	echo "   SUPABASE_URL_$$(echo $$CLUSTER_LABEL | tr '[:lower:]' '[:upper:]')=..." && \
	echo "   SUPABASE_KEY_$$(echo $$CLUSTER_LABEL | tr '[:lower:]' '[:upper:]')=..." && \
	echo "" && \
	echo "✅ Database cleanup instructions displayed for $$CLUSTER_LABEL"

argocd-verify: ## Step 6: Verify ArgoCD server is accessible at its URL (usage: make argocd-verify CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 6: Verifying ArgoCD server accessibility for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "🔍 Verifying tunnel configuration and name..." && \
	EXPECTED_TUNNEL_NAME="do-nyc2-dv-$$CLUSTER_LABEL" && \
	echo "   Expected tunnel name: $$EXPECTED_TUNNEL_NAME" && \
	if kubectl get pods -n cloudflare-tunnel-$$CLUSTER_LABEL >/dev/null 2>&1; then \
		TUNNEL_POD=$$(kubectl get pods -n cloudflare-tunnel-$$CLUSTER_LABEL -l app=cloudflared -o name | head -1) && \
		if [ -n "$$TUNNEL_POD" ]; then \
			echo "🔍 Checking tunnel logs for tunnel ID and connectivity..." && \
			TUNNEL_LOGS=$$(kubectl logs $$TUNNEL_POD -n cloudflare-tunnel-$$CLUSTER_LABEL --tail=10 2>/dev/null || echo "") && \
			if echo "$$TUNNEL_LOGS" | grep -q "Starting tunnel tunnelID="; then \
				TUNNEL_ID=$$(echo "$$TUNNEL_LOGS" | grep "Starting tunnel tunnelID=" | tail -1 | sed 's/.*tunnelID=\([a-f0-9\-]*\).*/\1/') && \
				echo "   Running tunnel ID: $$TUNNEL_ID" && \
				if echo "$$TUNNEL_LOGS" | grep -q "Registered tunnel connection"; then \
					CONNECTION_COUNT=$$(echo "$$TUNNEL_LOGS" | grep -c "Registered tunnel connection" || echo "0") && \
					echo "✅ Tunnel is connected with $$CONNECTION_COUNT active connections" && \
					echo "✅ Tunnel name verification: $$EXPECTED_TUNNEL_NAME"; \
				else \
					echo "⚠️  Tunnel may not be fully connected yet"; \
				fi; \
			else \
				echo "⚠️  Could not determine tunnel status from logs"; \
			fi; \
		else \
			echo "⚠️  No cloudflared pod found in namespace cloudflare-tunnel-$$CLUSTER_LABEL"; \
		fi; \
	else \
		echo "⚠️  Cloudflare tunnel namespace not found: cloudflare-tunnel-$$CLUSTER_LABEL"; \
	fi && \
	echo "🔍 Checking ArgoCD server pod status..." && \
	if ! kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=60s; then \
		echo "❌ FAILED: ArgoCD server pod not ready at $$(date '+%H:%M:%S')" && \
		echo "💡 Check pods: kubectl get pods -n argocd" && \
		exit 1; \
	fi && \
	ARGOCD_URL="https://$$CLUSTER_LABEL.argocd.diocesanvitality.org" && \
	echo "🌐 Testing ArgoCD URL: $$ARGOCD_URL" && \
	echo "🌐 Testing ArgoCD login screen (30 second timeout)..." && \
	TIMEOUT=30 && START_TIME=$$(date +%s) && \
	ARGOCD_ACCESSIBLE=false && \
	while true; do \
		RESPONSE=$$(curl -k -s --connect-timeout 5 --max-time 10 "$$ARGOCD_URL" 2>/dev/null || echo "") && \
		if echo "$$RESPONSE" | grep -q "Argo CD" && echo "$$RESPONSE" | grep -q "html"; then \
			echo "✅ ArgoCD login screen confirmed at $$ARGOCD_URL"; \
			ARGOCD_ACCESSIBLE=true && \
			break; \
		elif [ -n "$$RESPONSE" ]; then \
			echo "🔍 URL responding but not ArgoCD login screen - checking content..." && \
			if echo "$$RESPONSE" | grep -qi "error\|not found\|503\|502\|500"; then \
				echo "⚠️  Server error detected in response"; \
			else \
				echo "⚠️  Unexpected response content (not ArgoCD login)"; \
			fi; \
		fi && \
		CURRENT_TIME=$$(date +%s) && \
		if [ $$((CURRENT_TIME - START_TIME)) -gt $$TIMEOUT ]; then \
			echo "⚠️  ArgoCD login screen not accessible within 30 seconds" && \
			if [ -n "$$RESPONSE" ]; then \
				echo "💡 URL is responding but not showing ArgoCD login screen" && \
				echo "💡 Check tunnel configuration and ArgoCD server status"; \
			else \
				echo "💡 URL not responding - DNS/tunnel may need more time to propagate" && \
				echo "💡 Try accessing $$ARGOCD_URL manually in a few minutes"; \
			fi && \
			echo "💡 Check tunnel status: kubectl get pods -n cloudflare-tunnel-$$CLUSTER_LABEL" && \
			break; \
		fi && \
		echo "🔄 Waiting for ArgoCD login screen... ($$((CURRENT_TIME - START_TIME))s elapsed)" && \
		sleep 5; \
	done && \
	if [ "$$ARGOCD_ACCESSIBLE" = "true" ]; then \
		echo "🔐 ArgoCD login screen verified successfully"; \
	else \
		echo "⚠️  ArgoCD login screen verification incomplete - manual check recommended"; \
	fi && \
	echo "🔑 ArgoCD Login Information:" && \
	echo "   URL: $$ARGOCD_URL" && \
	echo "   Username: admin" && \
	if [ -f .argocd-admin-password ]; then \
		echo "   Password: $$(cat .argocd-admin-password)"; \
	else \
		echo "   Password: $$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"; \
	fi && \
	echo "✅ Step 6 Complete: ArgoCD server verified and accessible at $$ARGOCD_URL"

docker-build: ## Step 6.5: Build and push Docker images from appropriate branch (usage: make docker-build CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 6.5: Building and pushing Docker images for '$$CLUSTER_LABEL'..." && \
	echo "🎯 Setting source branch for $$CLUSTER_LABEL environment..." && \
	if [ "$$CLUSTER_LABEL" = "dev" ]; then \
		SOURCE_BRANCH="develop"; \
	elif [ "$$CLUSTER_LABEL" = "stg" ]; then \
		SOURCE_BRANCH="staging"; \
	else \
		SOURCE_BRANCH="main"; \
	fi && \
	echo "📋 Docker build configuration:" && \
	echo "   Environment: $$CLUSTER_LABEL" && \
	echo "   Source branch: $$SOURCE_BRANCH" && \
	echo "   Registry: Docker Hub (tomatl/diocesan-vitality)" && \
	echo "🔍 Checking current git branch..." && \
	CURRENT_BRANCH=$$(git branch --show-current) && \
	echo "   Current branch: $$CURRENT_BRANCH" && \
	if [ "$$CURRENT_BRANCH" != "$$SOURCE_BRANCH" ]; then \
		echo "🔄 Switching to $$SOURCE_BRANCH branch..." && \
		git fetch origin && \
		git checkout $$SOURCE_BRANCH && \
		git pull origin $$SOURCE_BRANCH && \
		echo "✅ Switched to $$SOURCE_BRANCH branch"; \
	else \
		echo "✅ Already on $$SOURCE_BRANCH branch" && \
		git pull origin $$SOURCE_BRANCH; \
	fi && \
	echo "🏷️  Generating image tags..." && \
	TIMESTAMP=$$(date +%Y-%m-%d-%H-%M-%S) && \
	IMAGE_TAG="$$CLUSTER_LABEL-$$TIMESTAMP" && \
	echo "   Image tag: $$IMAGE_TAG" && \
	echo "🔧 Checking Docker login..." && \
	if ! docker info >/dev/null 2>&1; then \
		echo "❌ FAILED: Docker daemon not running at $$(date '+%H:%M:%S')" && \
		echo "💡 Start Docker daemon and ensure you're logged in: docker login" && \
		exit 1; \
	fi && \
	echo "🏗️  Building multi-platform images..." && \
	echo "📦 Building backend image..." && \
	if ! docker buildx build --platform linux/amd64,linux/arm64 \
		-f backend/Dockerfile \
		-t tomatl/diocesan-vitality:backend-$$IMAGE_TAG \
		-t tomatl/diocesan-vitality:backend-$$CLUSTER_LABEL-latest \
		--push backend/; then \
		echo "❌ FAILED: Backend image build failed at $$(date '+%H:%M:%S')" && \
		exit 1; \
	fi && \
	echo "📦 Building frontend image..." && \
	if ! docker buildx build --platform linux/amd64,linux/arm64 \
		-f frontend/Dockerfile \
		-t tomatl/diocesan-vitality:frontend-$$IMAGE_TAG \
		-t tomatl/diocesan-vitality:frontend-$$CLUSTER_LABEL-latest \
		--push frontend/; then \
		echo "❌ FAILED: Frontend image build failed at $$(date '+%H:%M:%S')" && \
		exit 1; \
	fi && \
	echo "📦 Building pipeline image..." && \
	if ! docker buildx build --platform linux/amd64,linux/arm64 \
		-f Dockerfile.pipeline \
		-t tomatl/diocesan-vitality:pipeline-$$IMAGE_TAG \
		-t tomatl/diocesan-vitality:pipeline-$$CLUSTER_LABEL-latest \
		--push .; then \
		echo "❌ FAILED: Pipeline image build failed at $$(date '+%H:%M:%S')" && \
		exit 1; \
	fi && \
	echo "🎯 Updating Kubernetes manifests with new image tags..." && \
	MANIFEST_PATH="k8s/environments/development" && \
	if [ "$$CLUSTER_LABEL" = "stg" ]; then MANIFEST_PATH="k8s/environments/staging"; \
	elif [ "$$CLUSTER_LABEL" = "prd" ]; then MANIFEST_PATH="k8s/environments/production"; fi && \
	echo "   Manifest path: $$MANIFEST_PATH" && \
	if [ -f "$$MANIFEST_PATH/kustomization.yaml" ]; then \
		echo "🔄 Updating image tags in Kubernetes manifests..." && \
		if [ -f "$$MANIFEST_PATH/backend-deployment.yaml" ]; then \
			sed -i "s|image: tomatl/diocesan-vitality:backend-.*|image: tomatl/diocesan-vitality:backend-$$IMAGE_TAG|g" "$$MANIFEST_PATH/backend-deployment.yaml"; \
		fi && \
		if [ -f "$$MANIFEST_PATH/frontend-deployment.yaml" ]; then \
			sed -i "s|image: tomatl/diocesan-vitality:frontend-.*|image: tomatl/diocesan-vitality:frontend-$$IMAGE_TAG|g" "$$MANIFEST_PATH/frontend-deployment.yaml"; \
		fi && \
		if [ -f "$$MANIFEST_PATH/pipeline-deployment.yaml" ]; then \
			sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$$IMAGE_TAG|g" "$$MANIFEST_PATH/pipeline-deployment.yaml"; \
		fi && \
		echo "💾 Committing image tag updates to git..." && \
		git add $$MANIFEST_PATH/ && \
		git commit -m "Update $$CLUSTER_LABEL environment images to $$IMAGE_TAG" && \
		git push origin $$SOURCE_BRANCH && \
		echo "✅ Image tags updated and committed to $$SOURCE_BRANCH"; \
	else \
		echo "⚠️  Kubernetes manifests not found at $$MANIFEST_PATH" && \
		echo "💡 Images built and pushed, but manifests need manual update"; \
	fi && \
	echo "📊 Built images:" && \
	echo "   Backend: tomatl/diocesan-vitality:backend-$$IMAGE_TAG" && \
	echo "   Frontend: tomatl/diocesan-vitality:frontend-$$IMAGE_TAG" && \
	echo "   Pipeline: tomatl/diocesan-vitality:pipeline-$$IMAGE_TAG" && \
	echo "💡 GitOps will automatically deploy these images when ArgoCD syncs" && \
	echo "✅ Step 6.5 Complete: Docker images built and pushed from $$SOURCE_BRANCH branch"

app-deploy: ## Step 7: Verify diocesan-vitality application deployment via GitOps (usage: make app-deploy CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 7: Verifying diocesan-vitality application deployment for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "🔍 Checking that ArgoCD ApplicationSets are ready..." && \
	if ! kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=30s; then \
		echo "❌ FAILED: ArgoCD not ready at $$(date '+%H:%M:%S')" && \
		echo "💡 Run: make argocd-verify CLUSTER_LABEL=$$CLUSTER_LABEL" && \
		exit 1; \
	fi && \
	echo "🎯 GitOps configuration for $$CLUSTER_LABEL environment:" && \
	if [ "$$CLUSTER_LABEL" = "dev" ]; then \
		TARGET_BRANCH="develop"; \
		echo "   Source branch: $$TARGET_BRANCH (configured in ApplicationSet)"; \
	elif [ "$$CLUSTER_LABEL" = "stg" ]; then \
		TARGET_BRANCH="staging"; \
		echo "   Source branch: $$TARGET_BRANCH (configured in ApplicationSet)"; \
	else \
		TARGET_BRANCH="main"; \
		echo "   Source branch: $$TARGET_BRANCH (configured in ApplicationSet)"; \
	fi && \
	echo "   Application: diocesan-vitality-$$CLUSTER_LABEL" && \
	echo "   Namespace: diocesan-vitality-$$CLUSTER_LABEL" && \
	echo "🔄 Checking current application status..." && \
	if ! kubectl get application diocesan-vitality-$$CLUSTER_LABEL -n argocd >/dev/null 2>&1; then \
		echo "❌ FAILED: diocesan-vitality-$$CLUSTER_LABEL application not found at $$(date '+%H:%M:%S')" && \
		echo "💡 Ensure ArgoCD ApplicationSets are deployed: kubectl get applicationsets -n argocd" && \
		echo "💡 Check App-of-Apps root: kubectl get application root-applicationsets-$$CLUSTER_LABEL -n argocd" && \
		exit 1; \
	fi && \
	CURRENT_STATUS=$$(kubectl get application diocesan-vitality-$$CLUSTER_LABEL -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown") && \
	CURRENT_HEALTH=$$(kubectl get application diocesan-vitality-$$CLUSTER_LABEL -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown") && \
	CURRENT_BRANCH=$$(kubectl get application diocesan-vitality-$$CLUSTER_LABEL -n argocd -o jsonpath='{.spec.source.targetRevision}' 2>/dev/null || echo "Unknown") && \
	echo "   Current sync status: $$CURRENT_STATUS" && \
	echo "   Current health: $$CURRENT_HEALTH" && \
	echo "   Current branch: $$CURRENT_BRANCH" && \
	if [ "$$CURRENT_BRANCH" != "$$TARGET_BRANCH" ]; then \
		echo "⚠️  Application is configured for branch '$$CURRENT_BRANCH' but should be '$$TARGET_BRANCH'" && \
		echo "💡 Check ApplicationSet configuration: k8s/argocd/diocesan-vitality-$$CLUSTER_LABEL-applicationset.yaml"; \
	fi && \
	echo "⏳ Monitoring application sync status (up to 2 minutes)..." && \
	TIMEOUT=120 && START_TIME=$$(date +%s) && \
	while true; do \
		SYNC_STATUS=$$(kubectl get application diocesan-vitality-$$CLUSTER_LABEL -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown") && \
		HEALTH_STATUS=$$(kubectl get application diocesan-vitality-$$CLUSTER_LABEL -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown") && \
		if [ "$$SYNC_STATUS" = "Synced" ] && [ "$$HEALTH_STATUS" = "Healthy" ]; then \
			echo "✅ Application successfully synced and healthy via GitOps"; \
			break; \
		elif [ "$$SYNC_STATUS" = "Synced" ] && [ "$$HEALTH_STATUS" != "Healthy" ]; then \
			echo "⚠️  Application synced but not healthy: $$HEALTH_STATUS"; \
			echo "💡 This may be normal if container images are not yet available"; \
			break; \
		fi && \
		CURRENT_TIME=$$(date +%s) && \
		if [ $$((CURRENT_TIME - START_TIME)) -gt $$TIMEOUT ]; then \
			echo "⏳ Application still syncing after 2 minutes" && \
			echo "💡 Current status: Sync=$$SYNC_STATUS, Health=$$HEALTH_STATUS" && \
			echo "💡 GitOps deployments may take time for initial sync" && \
			break; \
		fi && \
		echo "🔄 Waiting for GitOps sync... Sync=$$SYNC_STATUS, Health=$$HEALTH_STATUS ($$((CURRENT_TIME - START_TIME))s elapsed)" && \
		sleep 10; \
	done && \
	echo "📊 Final deployment status:" && \
	kubectl get application diocesan-vitality-$$CLUSTER_LABEL -n argocd -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,BRANCH:.spec.source.targetRevision,REVISION:.status.sync.revision && \
	echo "🌐 Application URLs (when healthy):" && \
	echo "   Frontend: https://$$CLUSTER_LABEL.ui.diocesanvitality.org" && \
	echo "   Backend API: https://$$CLUSTER_LABEL.api.diocesanvitality.org" && \
	echo "💡 Monitor deployment: kubectl get pods -n diocesan-vitality-$$CLUSTER_LABEL" && \
	echo "💡 GitOps approach: Application configured via ApplicationSet to deploy from $$TARGET_BRANCH branch" && \
	echo "✅ Step 7 Complete: diocesan-vitality application verified via GitOps"

_install-helm: ## Install Helm CLI if not present
	@if ! command -v helm >/dev/null 2>&1; then \
		echo "📦 Installing Helm CLI..."; \
		curl -fsSL -o /tmp/get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 && \
		chmod 700 /tmp/get_helm.sh && \
		/tmp/get_helm.sh && \
		rm -f /tmp/get_helm.sh && \
		echo "✅ Helm CLI installed successfully"; \
	else \
		echo "✅ Helm CLI already installed"; \
	fi

_install-kubeseal: ## Install kubeseal CLI if not present
	@if ! command -v kubeseal >/dev/null 2>&1; then \
		echo "📦 Installing kubeseal CLI..."; \
		KUBESEAL_VERSION=$$(curl -s "https://api.github.com/repos/bitnami-labs/sealed-secrets/releases/latest" | grep -Po '"tag_name": "v\K[^"]*'); \
		ARCH=$$(uname -m); \
		case $$ARCH in \
			x86_64) ARCH="amd64" ;; \
			aarch64) ARCH="arm64" ;; \
			armv7l) ARCH="arm" ;; \
		esac && \
		wget -q "https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/kubeseal-$${KUBESEAL_VERSION}-linux-$${ARCH}.tar.gz" -O /tmp/kubeseal.tar.gz && \
		tar -xzf /tmp/kubeseal.tar.gz -C /tmp && \
		sudo mv /tmp/kubeseal /usr/local/bin/ && \
		sudo chmod +x /usr/local/bin/kubeseal && \
		rm -f /tmp/kubeseal.tar.gz && \
		echo "✅ kubeseal CLI installed successfully"; \
	else \
		echo "✅ kubeseal CLI already installed"; \
	fi
	@echo "🔑 ArgoCD Admin Password:"
	@if [ -f .argocd-admin-password ]; then \
		cat .argocd-admin-password && echo; \
	else \
		kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d && echo || echo "❌ ArgoCD not installed or password not found"; \
	fi

_update-kustomization-for-sealed-secret: ## Update kustomization.yaml to include sealed secret
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	KUSTOMIZATION_FILE="k8s/infrastructure/cloudflare-tunnel/environments/$$CLUSTER_LABEL/kustomization.yaml" && \
	SEALED_SECRET_FILE="cloudflared-token-sealedsecret.yaml" && \
	echo "🔧 Checking kustomization file: $$KUSTOMIZATION_FILE" && \
	if ! grep -q "$$SEALED_SECRET_FILE" "$$KUSTOMIZATION_FILE"; then \
		echo "📝 Adding sealed secret to kustomization resources..." && \
		sed -i "/resources:/a\  - $$SEALED_SECRET_FILE" "$$KUSTOMIZATION_FILE"; \
	else \
		echo "✅ Sealed secret already included in kustomization"; \
	fi

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
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	TUNNEL_NAME="do-nyc2-dv-$$CLUSTER_LABEL" && \
	if [ -f .env ]; then \
		CLOUDFLARE_API_TOKEN=$$(sed -n 's/^CLOUDFLARE_API_TOKEN=//p' .env | tr -d '\r\n"'"'"'') && \
		CLOUDFLARE_ACCOUNT_ID=$$(sed -n 's/^CLOUDFLARE_ACCOUNT_ID=//p' .env | tr -d '\r\n"'"'"'') && \
		if [ -n "$$CLOUDFLARE_API_TOKEN" ] && [ -n "$$CLOUDFLARE_ACCOUNT_ID" ]; then \
			TUNNELS_RESPONSE=$$(curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel" \
				-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
				-H "Content-Type: application/json" 2>/dev/null) && \
			TUNNEL_ID=$$(echo "$$TUNNELS_RESPONSE" | jq -r ".result[] | select(.name==\"$$TUNNEL_NAME\" and .deleted_at==null) | .id" 2>/dev/null | head -1) && \
			if [ -n "$$TUNNEL_ID" ] && [ "$$TUNNEL_ID" != "null" ]; then \
				TUNNEL_STATUS=$$(echo "$$TUNNELS_RESPONSE" | jq -r ".result[] | select(.name==\"$$TUNNEL_NAME\" and .deleted_at==null) | .status" 2>/dev/null | head -1) && \
				echo "  Tunnel: $$TUNNEL_NAME ($$TUNNEL_ID) - Status: $$TUNNEL_STATUS" && \
				kubectl get pods -n cloudflare-tunnel-$$CLUSTER_LABEL 2>/dev/null | grep cloudflared | head -1 || echo "  No cloudflared pod found"; \
			else \
				echo "  No tunnel found: $$TUNNEL_NAME"; \
			fi; \
		else \
			echo "  Cloudflare credentials not configured"; \
		fi; \
	else \
		echo "  No .env file found"; \
	fi

# Removed old infra-destroy - replaced with new 8-step version above

argocd-destroy: ## Destroy ArgoCD (usage: make argocd-destroy CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🧹 Destroying ArgoCD for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "🔧 Removing finalizers from ArgoCD applications..." && \
	kubectl get applications -n argocd -o name 2>/dev/null | xargs -r -I {} kubectl patch {} -n argocd --type='merge' -p='{"metadata":{"finalizers":null}}' || true && \
	echo "🗑️  Deleting ArgoCD namespace..." && \
	kubectl delete namespace argocd --ignore-not-found=true

# Removed old cluster-destroy - replaced with new Step 3b version above

tunnel-verify: ## Generate tunnel token file for sealed secrets (usage: make tunnel-verify CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔍 Generating tunnel token for '$$CLUSTER_LABEL'..." && \
	TUNNEL_NAME="do-nyc2-dv-$$CLUSTER_LABEL" && \
	$(MAKE) tunnel-auth && \
	CLOUDFLARE_API_TOKEN=$$(sed -n 's/^CLOUDFLARE_API_TOKEN=//p' .env | tr -d '\r\n"'"'"'') && \
	CLOUDFLARE_ACCOUNT_ID=$$(sed -n 's/^CLOUDFLARE_ACCOUNT_ID=//p' .env | tr -d '\r\n"'"'"'') && \
	export CLOUDFLARE_API_TOKEN="$$CLOUDFLARE_API_TOKEN" && \
	echo "🔧 Fetching tunnel information..." && \
	TUNNELS_RESPONSE=$$(curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel" \
		-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN" \
		-H "Content-Type: application/json") && \
	TUNNEL_ID=$$(echo "$$TUNNELS_RESPONSE" | jq -r ".result[] | select(.name==\"$$TUNNEL_NAME\" and .deleted_at==null) | .id" 2>/dev/null | head -1) && \
	if [ -z "$$TUNNEL_ID" ] || [ "$$TUNNEL_ID" = "null" ]; then \
		echo "❌ Tunnel $$TUNNEL_NAME does not exist. Run 'make tunnel-create CLUSTER_LABEL=$$CLUSTER_LABEL' first." && \
		exit 1; \
	fi && \
	echo "🔍 Found tunnel: $$TUNNEL_NAME ($$TUNNEL_ID)" && \
	echo "🔐 Generating tunnel token..." && \
	TOKEN_RESPONSE=$$(curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel/$$TUNNEL_ID/token" \
		-H "Authorization: Bearer $$CLOUDFLARE_API_TOKEN") && \
	if echo "$$TOKEN_RESPONSE" | jq -e '.success == true' >/dev/null 2>&1; then \
		TUNNEL_TOKEN=$$(echo "$$TOKEN_RESPONSE" | jq -r '.result' 2>/dev/null) && \
		if [ -n "$$TUNNEL_TOKEN" ] && [ "$$TUNNEL_TOKEN" != "null" ]; then \
			echo "✅ Tunnel token generated successfully" && \
			echo "🔍 Adding base64 padding if needed..." && \
			TOKEN_LEN=$$(echo -n "$$TUNNEL_TOKEN" | wc -c) && \
			PADDING_NEEDED=$$((4 - TOKEN_LEN % 4)) && \
			if [ $$PADDING_NEEDED -ne 4 ]; then \
				PADDING=$$(printf '%*s' $$PADDING_NEEDED '' | tr ' ' '=') && \
				TUNNEL_TOKEN="$$TUNNEL_TOKEN$$PADDING"; \
			fi && \
			echo "💾 Saving tunnel token to .tunnel-token-$$CLUSTER_LABEL..." && \
			echo "TUNNEL_TOKEN_$$CLUSTER_LABEL=$$TUNNEL_TOKEN" > .tunnel-token-$$CLUSTER_LABEL && \
			echo "✅ Tunnel token saved to .tunnel-token-$$CLUSTER_LABEL" && \
			echo "🔍 Token preview: $$(echo "$$TUNNEL_TOKEN" | cut -c1-20)..."; \
		else \
			echo "❌ Failed to extract tunnel token from API response" && \
			exit 1; \
		fi; \
	else \
		echo "❌ Failed to generate tunnel token. API response:" && \
		echo "$$TOKEN_RESPONSE" && \
		exit 1; \
	fi

infra-test: ## Step 6: Integration testing and cleanup (usage: make infra-test CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🧪 Step 6: Running integration tests and cleanup for '$$CLUSTER_LABEL'..." && \
	echo "🔍 Testing cluster connectivity..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	kubectl get nodes >/dev/null && \
	echo "✅ Cluster connectivity test passed" && \
	echo "🔍 Testing ArgoCD installation..." && \
	kubectl get pods -n argocd | grep -q "argocd-server.*Running" && \
	echo "✅ ArgoCD installation test passed" && \
	echo "🔍 Testing ApplicationSets..." && \
	kubectl get applicationsets -n argocd | grep -q "diocesan-vitality-$$CLUSTER_LABEL" && \
	echo "✅ ApplicationSets test passed" && \
	echo "🔍 Testing sealed-secrets controller..." && \
	kubectl get pods -n kube-system -l app.kubernetes.io/name=sealed-secrets | grep -q "Running" && \
	echo "✅ Sealed-secrets controller test passed" && \
	echo "🧹 Cleaning up temporary files..." && \
	rm -f .tunnel-token-$$CLUSTER_LABEL && \
	echo "✅ Temporary tunnel token file removed" && \
	echo "🔐 Verifying no sensitive data in environment..." && \
	if env | grep -q "TUNNEL_TOKEN"; then \
		echo "⚠️  Found tunnel tokens in environment - consider unsetting them"; \
	else \
		echo "✅ No tunnel tokens found in environment"; \
	fi && \
	echo "📊 Final infrastructure status:" && \
	$(MAKE) infra-status CLUSTER_LABEL=$$CLUSTER_LABEL
	@echo "✅ Step 6 Complete: Integration tests passed and cleanup completed"

# Cluster Scaling Commands
# ========================

cluster-scale-dev-0: ## Scale development cluster to zero nodes (usage: make cluster-scale-dev-0)
	@echo "⏸️  Scaling development cluster to zero nodes..." && \
	echo "   Cluster: dv-dev" && \
	echo "   slow-pool: 1 → 0 nodes" && \
	echo "   fast-pool: 2 → 0 nodes" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-dev slow-pool --count 0" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-dev fast-pool --count 0" && \
	echo "✅ Development cluster scaled to 0 nodes" && \
	echo "💡 This saves costs when cluster is not in use" && \
	echo "💡 To restore: make cluster-scale-dev-normal"

cluster-scale-stg-0: ## Scale staging cluster to zero nodes (usage: make cluster-scale-stg-0)
	@echo "⏸️  Scaling staging cluster to zero nodes..." && \
	echo "   Cluster: dv-stg" && \
	echo "   slow-pool: 1 → 0 nodes" && \
	echo "   fast-pool: 2 → 0 nodes" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-stg slow-pool --count 0" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-stg fast-pool --count 0" && \
	echo "✅ Staging cluster scaled to 0 nodes" && \
	echo "💡 This saves costs when cluster is not in use" && \
	echo "💡 To restore: make cluster-scale-stg-normal"

cluster-scale-prd-0: ## Scale production cluster to zero nodes (usage: make cluster-scale-prd-0)
	@echo "🚨 WARNING: Scaling PRODUCTION cluster to zero nodes!" && \
	echo "   This will make production services unavailable" && \
	read -p "Type 'yes' to continue: " CONFIRM </dev/tty && \
	if [ "$$CONFIRM" != "yes" ]; then \
		echo "❌ Operation cancelled"; \
		exit 1; \
	fi && \
	echo "⏸️  Scaling production cluster to zero nodes..." && \
	echo "   Cluster: dv-prd" && \
	echo "   slow-pool: 1 → 0 nodes" && \
	echo "   fast-pool: 2 → 0 nodes" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-prd slow-pool --count 0" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-prd fast-pool --count 0" && \
	echo "✅ Production cluster scaled to 0 nodes" && \
	echo "💡 To restore: make cluster-scale-prd-normal"

cluster-scale-all-0: ## Scale all clusters to zero nodes (usage: make cluster-scale-all-0)
	@echo "🚨 WARNING: Scaling ALL clusters to zero nodes!" && \
	echo "   This will make all environments unavailable" && \
	read -p "Type 'yes' to continue: " CONFIRM </dev/tty && \
	if [ "$$CONFIRM" != "yes" ]; then \
		echo "❌ Operation cancelled"; \
		exit 1; \
	fi && \
	echo "⏸️  Scaling all clusters to zero nodes..." && \
	$(MAKE) cluster-scale-dev-0 && \
	$(MAKE) cluster-scale-stg-0 && \
	$(MAKE) cluster-scale-prd-0 && \
	echo "✅ All clusters scaled to 0 nodes"

cluster-scale-dev-normal: ## Restore development cluster to normal size (usage: make cluster-scale-dev-normal)
	@echo "▶️  Restoring development cluster to normal size..." && \
	echo "   Cluster: dv-dev" && \
	echo "   slow-pool: 0 → 1 node" && \
	echo "   fast-pool: 0 → 2 nodes" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-dev slow-pool --count 1" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-dev fast-pool --count 2" && \
	echo "✅ Development cluster restored to normal size (1 slow + 2 fast nodes)" && \
	echo "⏳ Nodes will take 2-3 minutes to provision and become ready"

cluster-scale-stg-normal: ## Restore staging cluster to normal size (usage: make cluster-scale-stg-normal)
	@echo "▶️  Restoring staging cluster to normal size..." && \
	echo "   Cluster: dv-stg" && \
	echo "   slow-pool: 0 → 1 node" && \
	echo "   fast-pool: 0 → 2 nodes" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-stg slow-pool --count 1" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-stg fast-pool --count 2" && \
	echo "✅ Staging cluster restored to normal size (1 slow + 2 fast nodes)" && \
	echo "⏳ Nodes will take 2-3 minutes to provision and become ready"

cluster-scale-prd-normal: ## Restore production cluster to normal size (usage: make cluster-scale-prd-normal)
	@echo "▶️  Restoring production cluster to normal size..." && \
	echo "   Cluster: dv-prd" && \
	echo "   slow-pool: 0 → 1 node" && \
	echo "   fast-pool: 0 → 2 nodes" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-prd slow-pool --count 1" && \
	$(MAKE) _doctl-exec DOCTL_CMD="kubernetes cluster node-pool update dv-prd fast-pool --count 2" && \
	echo "✅ Production cluster restored to normal size (1 slow + 2 fast nodes)" && \
	echo "⏳ Nodes will take 2-3 minutes to provision and become ready"

cluster-scale-all-normal: ## Restore all clusters to normal size (usage: make cluster-scale-all-normal)
	@echo "▶️  Restoring all clusters to normal size..." && \
	$(MAKE) cluster-scale-dev-normal && \
	$(MAKE) cluster-scale-stg-normal && \
	$(MAKE) cluster-scale-prd-normal && \
	echo "✅ All clusters restored to normal size"
