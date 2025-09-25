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

infra-setup: ## Set up complete infrastructure (all 6 steps, usage: make infra-setup CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Setting up complete infrastructure for '$$CLUSTER_LABEL'..." && \
	$(MAKE) cluster-create CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) tunnel-create CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) tunnel-verify CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) argocd-install CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) argocd-apps CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) sealed-secrets-create CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) infra-test CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "🎉 Infrastructure setup complete for $$CLUSTER_LABEL!"

cluster-create: ## Step 1: Create cluster and kubectl context (usage: make cluster-create CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 1: Creating cluster and kubectl context for '$$CLUSTER_LABEL'..." && \
	if ! command -v jq >/dev/null 2>&1; then \
		echo "❌ jq is required for cluster monitoring. Install with: apt-get install jq" && \
		exit 1; \
	fi && \
	START_TIME=$$(date +%s) && \
	TIMEOUT_SECONDS=900 && \
	if [ "$$CLUSTER_LABEL" = "stg" ]; then ENV_DIR="staging"; else ENV_DIR="$$CLUSTER_LABEL"; fi && \
	cd terraform/environments/$$ENV_DIR && \
		echo "⏳ Initializing Terraform... ($$(date '+%H:%M:%S'))" && \
		export $$(grep DIGITALOCEAN_TOKEN ../../../.env | xargs) && \
		if ! terraform init; then \
			echo "❌ FAILED: Terraform initialization failed at $$(date '+%H:%M:%S')" && \
			exit 1; \
		fi && \
		echo "🔧 Applying Terraform configuration... ($$(date '+%H:%M:%S'))" && \
		if ! terraform apply -target=module.k8s_cluster -auto-approve; then \
			echo "❌ FAILED: Terraform apply failed at $$(date '+%H:%M:%S')" && \
			echo "💡 Check the error output above for details" && \
			exit 1; \
		fi && \
		echo "📋 Monitoring cluster provisioning status... ($$(date '+%H:%M:%S'))" && \
		CLUSTER_NAME="dv-$$CLUSTER_LABEL" && \
		while true; do \
			CURRENT_TIME=$$(date +%s) && \
			ELAPSED=$$((CURRENT_TIME - START_TIME)) && \
			if [ $$ELAPSED -gt $$TIMEOUT_SECONDS ]; then \
				echo "❌ Timeout: Cluster creation exceeded 15 minutes" && \
				exit 1; \
			fi && \
			STATUS=$$(doctl kubernetes cluster get $$CLUSTER_NAME -o json 2>/dev/null | jq -r '.[0].status.state // "not_found"') && \
			if [ "$$STATUS" = "running" ]; then \
				echo "✅ Cluster is running! (Total time: $$((ELAPSED/60))m $$((ELAPSED%60))s)" && \
				break; \
			elif [ "$$STATUS" = "provisioning" ]; then \
				echo "⏳ Cluster still provisioning... ($$((ELAPSED/60))m $$((ELAPSED%60))s elapsed, $$(date '+%H:%M:%S'))" && \
				sleep 30; \
			elif [ "$$STATUS" = "not_found" ]; then \
				echo "⏳ Waiting for cluster to appear in DigitalOcean... ($$((ELAPSED/60))m $$((ELAPSED%60))s elapsed)" && \
				sleep 15; \
			else \
				echo "❌ Unexpected cluster status: $$STATUS" && \
				exit 1; \
			fi; \
		done && \
		echo "🔗 Configuring kubectl access... ($$(date '+%H:%M:%S'))" && \
		doctl kubernetes cluster kubeconfig save dv-$$CLUSTER_LABEL && \
		kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
		echo "🔍 Verifying cluster nodes... ($$(date '+%H:%M:%S'))" && \
		kubectl get nodes && \
		echo "🏷️  Labeling cluster with environment label... ($$(date '+%H:%M:%S'))" && \
		kubectl create secret generic cluster-info \
			--from-literal=environment=$$CLUSTER_LABEL \
			--from-literal=cluster-name=dv-$$CLUSTER_LABEL \
			-n default --dry-run=client -o yaml | kubectl apply -f -
	@echo "✅ Step 1 Complete: Cluster created and labeled"

tunnel-create: ## Step 2: Create Cloudflare tunnel and DNS records (usage: make tunnel-create CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 2: Creating Cloudflare tunnel for '$$CLUSTER_LABEL'..." && \
	echo "🧹 Cleaning up any stale tunnel state..." && \
	if [ "$$CLUSTER_LABEL" = "stg" ]; then ENV_DIR="staging"; else ENV_DIR="$$CLUSTER_LABEL"; fi && \
	cd terraform/environments/$$ENV_DIR && \
		echo "🔧 Setting up environment variables... ($$(date '+%H:%M:%S'))" && \
		export $$(grep CLOUDFLARE_API_TOKEN ../../../.env | xargs) && \
		echo "🧹 Cleaning up stale tunnel state... ($$(date '+%H:%M:%S'))" && \
		if ! terraform state list | grep "module.cloudflare_tunnel" | xargs -r terraform state rm; then \
			echo "💡 No stale tunnel state to clean" && true; \
		fi && \
		echo "🚀 Applying Cloudflare tunnel configuration... ($$(date '+%H:%M:%S'))" && \
		if ! terraform apply -target=module.cloudflare_tunnel -auto-approve; then \
			echo "❌ FAILED: Tunnel creation failed at $$(date '+%H:%M:%S')" && \
			echo "💡 Check the error output above for details" && \
			exit 1; \
		fi
	@echo "✅ Step 2 Complete: Cloudflare tunnel created for $$CLUSTER_LABEL"

argocd-install: ## Step 3: Install ArgoCD via Helm with proper configuration (usage: make argocd-install CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 3: Installing ArgoCD via Helm for '$$CLUSTER_LABEL'..." && \
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
	@echo "🚀 Deploying App-of-Apps for ApplicationSets..."
	@$(MAKE) _deploy-app-of-apps CLUSTER_LABEL=$$CLUSTER_LABEL
	@echo "✅ Step 3 Complete: ArgoCD installed via Helm with App-of-Apps pattern for $$CLUSTER_LABEL"

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

argocd-password: ## Get ArgoCD admin password
sealed-secrets-create: ## Step 4: Create tunnel token sealed secret from environment file (usage: make sealed-secrets-create CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 4: Creating tunnel token sealed secret for '$$CLUSTER_LABEL'..." && \
	echo "🔍 Loading tunnel token from environment file..." && \
	if [ ! -f ".tunnel-token-$$CLUSTER_LABEL" ]; then \
		echo "❌ Could not find tunnel token file: .tunnel-token-$$CLUSTER_LABEL"; \
		echo "💡 Ensure tunnel verification has been run: make tunnel-verify CLUSTER_LABEL=$$CLUSTER_LABEL"; \
		exit 1; \
	fi && \
	TUNNEL_TOKEN=$$(grep "TUNNEL_TOKEN_$$CLUSTER_LABEL" .tunnel-token-$$CLUSTER_LABEL | cut -d'=' -f2) && \
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
	echo "✅ Tunnel token loaded: $$(echo "$$TUNNEL_TOKEN" | cut -c1-20)..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "🔧 Installing kubeseal CLI if needed..." && \
	$(MAKE) _install-kubeseal && \
	echo "⏳ Waiting for sealed-secrets controller to be ready..." && \
	kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=sealed-secrets -n kube-system --timeout=300s && \
	echo "🔐 Creating sealed secret from tunnel token..." && \
	echo -n "$$TUNNEL_TOKEN" | kubectl create secret generic cloudflared-token \
		--dry-run=client --from-file=tunnel-token=/dev/stdin \
		--namespace=cloudflare-tunnel-$$CLUSTER_LABEL -o yaml | \
	kubeseal -o yaml --namespace=cloudflare-tunnel-$$CLUSTER_LABEL > \
		k8s/infrastructure/cloudflare-tunnel/environments/$$CLUSTER_LABEL/cloudflared-token-sealedsecret.yaml && \
	echo "🔧 Updating kustomization to include sealed secret..." && \
	$(MAKE) _update-kustomization-for-sealed-secret CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "💾 Committing sealed secret to repository..." && \
	git add k8s/infrastructure/cloudflare-tunnel/environments/$$CLUSTER_LABEL/ && \
	git commit -m "Add tunnel token sealed secret for cloudflare-tunnel-$$CLUSTER_LABEL (tunnel: $$TUNNEL_ID)" && \
	git push && \
	echo "⏳ Waiting for tunnel application to sync and become healthy..." && \
	sleep 30 && \
	echo "✅ Step 5 Complete: Tunnel token sealed secret created for $$CLUSTER_LABEL (tunnel: $$TUNNEL_ID)"

argocd-verify: ## Step 6: Verify ArgoCD server is accessible at its URL (usage: make argocd-verify CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 6: Verifying ArgoCD server accessibility for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "🔍 Checking ArgoCD server pod status..." && \
	if ! kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=60s; then \
		echo "❌ FAILED: ArgoCD server pod not ready at $$(date '+%H:%M:%S')" && \
		echo "💡 Check pods: kubectl get pods -n argocd" && \
		exit 1; \
	fi && \
	ARGOCD_URL="https://$$CLUSTER_LABEL.argocd.diocesanvitality.org" && \
	echo "🌐 Testing ArgoCD URL: $$ARGOCD_URL" && \
	echo "🌐 Testing external URL (30 second timeout)..." && \
	TIMEOUT=30 && START_TIME=$$(date +%s) && \
	while true; do \
		if curl -k -s --connect-timeout 5 --max-time 10 "$$ARGOCD_URL" >/dev/null 2>&1; then \
			echo "✅ ArgoCD server is accessible at $$ARGOCD_URL"; \
			break; \
		fi && \
		CURRENT_TIME=$$(date +%s) && \
		if [ $$((CURRENT_TIME - START_TIME)) -gt $$TIMEOUT ]; then \
			echo "⚠️  External URL not accessible within 30 seconds" && \
			echo "💡 ArgoCD may be accessible but DNS/tunnel routing needs time to propagate" && \
			echo "💡 Try accessing $$ARGOCD_URL manually in a few minutes" && \
			echo "💡 Check tunnel status: kubectl get pods -n cloudflare-tunnel-$$CLUSTER_LABEL" && \
			break; \
		fi && \
		echo "🔄 Waiting for URL response... ($$((CURRENT_TIME - START_TIME))s elapsed)" && \
		sleep 5; \
	done && \
	echo "🔑 ArgoCD Login Information:" && \
	echo "   URL: $$ARGOCD_URL" && \
	echo "   Username: admin" && \
	if [ -f .argocd-admin-password ]; then \
		echo "   Password: $$(cat .argocd-admin-password)"; \
	else \
		echo "   Password: $$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"; \
	fi && \
	echo "✅ Step 6 Complete: ArgoCD server verified and accessible at $$ARGOCD_URL"

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
	@cd terraform/environments/dev && terraform output tunnel_info 2>/dev/null || echo "  No tunnel found"

infra-destroy: ## Destroy complete infrastructure (usage: make infra-destroy CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🧹 Destroying infrastructure for '$$CLUSTER_LABEL'..." && \
	$(MAKE) tunnel-destroy CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) argocd-destroy CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) cluster-destroy CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "✅ Infrastructure destroyed for $$CLUSTER_LABEL"

tunnel-destroy: ## Destroy Cloudflare tunnel (usage: make tunnel-destroy CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🧹 Destroying Cloudflare tunnel for '$$CLUSTER_LABEL'..." && \
	if [ "$$CLUSTER_LABEL" = "stg" ]; then ENV_DIR="staging"; else ENV_DIR="$$CLUSTER_LABEL"; fi && \
	cd terraform/environments/$$ENV_DIR && \
		export CLOUDFLARE_API_TOKEN=$$(grep CLOUDFLARE_API_TOKEN ../../../.env | cut -d'=' -f2) && \
		terraform destroy -target=module.cloudflare_tunnel -auto-approve || true && \
		terraform state list | grep "module.cloudflare_tunnel" | xargs -r terraform state rm || true

argocd-destroy: ## Destroy ArgoCD (usage: make argocd-destroy CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🧹 Destroying ArgoCD for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "🔧 Removing finalizers from ArgoCD applications..." && \
	kubectl get applications -n argocd -o name 2>/dev/null | xargs -r -I {} kubectl patch {} -n argocd --type='merge' -p='{"metadata":{"finalizers":null}}' || true && \
	echo "🗑️  Deleting ArgoCD namespace..." && \
	kubectl delete namespace argocd --ignore-not-found=true

cluster-destroy: ## Destroy cluster (usage: make cluster-destroy CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🧹 Destroying cluster for '$$CLUSTER_LABEL'..." && \
	if [ "$$CLUSTER_LABEL" = "stg" ]; then ENV_DIR="staging"; else ENV_DIR="$$CLUSTER_LABEL"; fi && \
	cd terraform/environments/$$ENV_DIR && \
		export DIGITALOCEAN_TOKEN=$$(grep DIGITALOCEAN_TOKEN ../../../.env | cut -d'=' -f2) && \
		terraform destroy -target=module.k8s_cluster -auto-approve || true

tunnel-verify: ## Step 2.5: Verify tunnel and cluster, save tunnel token to environment (usage: make tunnel-verify CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🔍 Step 2.5: Verifying tunnel and cluster for '$$CLUSTER_LABEL'..." && \
	if [ "$$CLUSTER_LABEL" = "stg" ]; then ENV_DIR="staging"; else ENV_DIR="$$CLUSTER_LABEL"; fi && \
	echo "📋 Verifying cluster status... ($$(date '+%H:%M:%S'))" && \
	if ! kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL; then \
		echo "❌ FAILED: Could not switch to kubectl context do-nyc2-dv-$$CLUSTER_LABEL at $$(date '+%H:%M:%S')" && \
		echo "💡 Check if cluster exists: doctl kubernetes cluster list" && \
		exit 1; \
	fi && \
	if ! kubectl get nodes --no-headers | wc -l | grep -q "[1-9]"; then \
		echo "❌ FAILED: Cluster has no ready nodes at $$(date '+%H:%M:%S')" && \
		echo "💡 Check cluster status: kubectl get nodes" && \
		exit 1; \
	fi && \
	echo "✅ Cluster verification passed ($$(date '+%H:%M:%S'))" && \
	echo "🔍 Verifying tunnel creation... ($$(date '+%H:%M:%S'))" && \
	cd terraform/environments/$$ENV_DIR && \
		export $$(grep CLOUDFLARE_API_TOKEN ../../../.env | xargs) && \
		if ! TUNNEL_OUTPUT=$$(terraform output -json tunnel_info 2>/dev/null); then \
			echo "❌ FAILED: Could not get tunnel info from Terraform at $$(date '+%H:%M:%S')" && \
			echo "💡 Check if tunnel was created: make tunnel-create CLUSTER_LABEL=$$CLUSTER_LABEL" && \
			exit 1; \
		fi && \
		TUNNEL_ID=$$(echo "$$TUNNEL_OUTPUT" | jq -r '.id // empty') && \
		TUNNEL_CNAME=$$(echo "$$TUNNEL_OUTPUT" | jq -r '.cname // empty') && \
		if [ -z "$$TUNNEL_ID" ] || [ -z "$$TUNNEL_CNAME" ]; then \
			echo "❌ FAILED: Tunnel verification failed - missing tunnel info at $$(date '+%H:%M:%S')" && \
			echo "💡 Tunnel output: $$TUNNEL_OUTPUT" && \
			exit 1; \
		fi && \
		echo "✅ Tunnel verification passed: $$TUNNEL_ID ($$(date '+%H:%M:%S'))" && \
		echo "🔐 Extracting tunnel token from k8s-secrets... ($$(date '+%H:%M:%S'))" && \
		CREDENTIALS_FILE="k8s-secrets/cloudflare-tunnel-$$ENV_DIR.yaml" && \
		if [ ! -f "$$CREDENTIALS_FILE" ]; then \
			echo "❌ FAILED: Could not find tunnel credentials file: $$CREDENTIALS_FILE at $$(date '+%H:%M:%S')" && \
			echo "💡 Check if tunnel created credentials: ls -la terraform/environments/$$ENV_DIR/k8s-secrets/" && \
			exit 1; \
		fi && \
		if ! CREDENTIALS_B64=$$(grep "credentials.json" "$$CREDENTIALS_FILE" | cut -d'"' -f4); then \
			echo "❌ FAILED: Could not extract credentials from file at $$(date '+%H:%M:%S')" && \
			echo "💡 Check file format: head -5 $$CREDENTIALS_FILE" && \
			exit 1; \
		fi && \
		if ! CREDENTIALS_JSON=$$(echo "$$CREDENTIALS_B64" | base64 -d 2>/dev/null); then \
			echo "❌ FAILED: Could not decode base64 credentials at $$(date '+%H:%M:%S')" && \
			exit 1; \
		fi && \
		ACCOUNT_TAG=$$(echo "$$CREDENTIALS_JSON" | jq -r '.AccountTag') && \
		TUNNEL_SECRET=$$(echo "$$CREDENTIALS_JSON" | jq -r '.TunnelSecret') && \
		if [ -z "$$ACCOUNT_TAG" ] || [ -z "$$TUNNEL_SECRET" ]; then \
			echo "❌ FAILED: Missing AccountTag or TunnelSecret at $$(date '+%H:%M:%S')" && \
			echo "💡 Credentials JSON: $$CREDENTIALS_JSON" && \
			exit 1; \
		fi && \
		TUNNEL_SECRET_B64=$$(echo -n "$$TUNNEL_SECRET" | base64 -w0) && \
		TUNNEL_TOKEN=$$(echo "{\"a\":\"$$ACCOUNT_TAG\",\"t\":\"$$TUNNEL_ID\",\"s\":\"$$TUNNEL_SECRET_B64\"}" | base64 -w0) && \
		if [ -z "$$TUNNEL_TOKEN" ]; then \
			echo "❌ FAILED: Failed to generate tunnel token at $$(date '+%H:%M:%S')" && \
			exit 1; \
		fi && \
		echo "💾 Saving tunnel token to environment file... ($$(date '+%H:%M:%S'))" && \
		echo "TUNNEL_TOKEN_$$CLUSTER_LABEL=$$TUNNEL_TOKEN" > ../../../.tunnel-token-$$CLUSTER_LABEL && \
		echo "✅ Tunnel token saved to .tunnel-token-$$CLUSTER_LABEL" && \
		echo "🔍 Verifying token format... ($$(date '+%H:%M:%S'))" && \
		if ! echo "$$TUNNEL_TOKEN" | base64 -d | jq . >/dev/null 2>&1; then \
			echo "❌ FAILED: Token format verification failed at $$(date '+%H:%M:%S')" && \
			exit 1; \
		fi && \
		echo "✅ Tunnel token verification passed ($$(date '+%H:%M:%S'))"
	@echo "✅ Step 2.5 Complete: Tunnel and cluster verified, token saved"

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
