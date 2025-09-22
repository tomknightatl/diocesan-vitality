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
	@flake8 . --exclude=venv,node_modules,frontend/node_modules
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

infra-setup: ## Set up complete infrastructure (all 5 steps, usage: make infra-setup CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Setting up complete infrastructure for '$$CLUSTER_LABEL'..." && \
	$(MAKE) cluster-create CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) tunnel-create CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) argocd-install CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) argocd-apps CLUSTER_LABEL=$$CLUSTER_LABEL && \
	$(MAKE) sealed-secrets-create CLUSTER_LABEL=$$CLUSTER_LABEL && \
	echo "🎉 Infrastructure setup complete for $$CLUSTER_LABEL!"

cluster-create: ## Step 1: Create cluster and kubectl context (usage: make cluster-create CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 1: Creating cluster and kubectl context for '$$CLUSTER_LABEL'..." && \
	if ! command -v jq >/dev/null 2>&1; then \
		echo "❌ jq is required for cluster monitoring. Install with: apt-get install jq" && \
		exit 1; \
	fi && \
	START_TIME=$$(date +%s) && \
	TIMEOUT_SECONDS=1800 && \
	if [ "$$CLUSTER_LABEL" = "stg" ]; then ENV_DIR="staging"; else ENV_DIR="$$CLUSTER_LABEL"; fi && \
	cd terraform/environments/$$ENV_DIR && \
		echo "⏳ Initializing Terraform... ($$(date '+%H:%M:%S'))" && \
		export DIGITALOCEAN_TOKEN=$$(grep DIGITALOCEAN_TOKEN ../../../.env | cut -d'=' -f2) && \
		terraform init && \
		echo "🔧 Applying Terraform configuration... ($$(date '+%H:%M:%S'))" && \
		terraform apply -target=module.k8s_cluster -auto-approve && \
		echo "📋 Monitoring cluster provisioning status... ($$(date '+%H:%M:%S'))" && \
		CLUSTER_NAME="dv-$$CLUSTER_LABEL" && \
		while true; do \
			CURRENT_TIME=$$(date +%s) && \
			ELAPSED=$$((CURRENT_TIME - START_TIME)) && \
			if [ $$ELAPSED -gt $$TIMEOUT_SECONDS ]; then \
				echo "❌ Timeout: Cluster creation exceeded 30 minutes" && \
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
		export CLOUDFLARE_API_TOKEN=$$(grep CLOUDFLARE_API_TOKEN ../../../.env | cut -d'=' -f2) && \
		export TF_VAR_cloudflare_account_id=$$(grep CLOUDFLARE_ACCOUNT_ID ../../../.env | cut -d'=' -f2) && \
		export TF_VAR_cloudflare_zone_id=$$(grep CLOUDFLARE_ZONE_ID ../../../.env | cut -d'=' -f2) && \
		terraform state list | grep "module.cloudflare_tunnel" | xargs -r terraform state rm || true && \
		terraform apply -target=module.cloudflare_tunnel -auto-approve
	@echo "✅ Step 2 Complete: Cloudflare tunnel created for $$CLUSTER_LABEL"

argocd-install: ## Step 3: Install ArgoCD via Helm with proper configuration (usage: make argocd-install CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 3: Installing ArgoCD via Helm for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
		echo "🔧 Installing Helm if needed..." && \
		$(MAKE) _install-helm && \
		echo "📦 Adding ArgoCD Helm repository..." && \
		helm repo add argo https://argoproj.github.io/argo-helm && \
		helm repo update && \
		kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f - && \
		echo "🚀 Installing ArgoCD with values-$$CLUSTER_LABEL.yaml..." && \
		helm upgrade --install argocd argo/argo-cd \
			--namespace argocd \
			--values k8s/infrastructure/argocd/values-$$CLUSTER_LABEL.yaml \
			--wait --timeout=20m && \
		echo "⏳ Waiting for ArgoCD server to be ready..." && \
		kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=600s && \
		echo "🔧 Configuring repository access..." && \
		while ! kubectl get configmap argocd-cm -n argocd >/dev/null 2>&1; do sleep 2; done && \
		sleep 5 && \
		kubectl patch configmap argocd-cm -n argocd --patch '{"data":{"repositories":"- url: https://github.com/tomknightatl/diocesan-vitality.git"}}'
	@echo "🔧 Setting up custom ArgoCD password..."
	@$(MAKE) _setup-argocd-password CLUSTER_LABEL=$$CLUSTER_LABEL
	@echo "🏷️  Registering cluster with ArgoCD..."
	@$(MAKE) _register-cluster-with-argocd CLUSTER_LABEL=$$CLUSTER_LABEL
	@echo "✅ Step 3 Complete: ArgoCD installed via Helm with insecure mode for $$CLUSTER_LABEL"

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

argocd-apps: ## Step 4: Install ArgoCD ApplicationSets (usage: make argocd-apps CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 4: Installing ArgoCD ApplicationSets for '$$CLUSTER_LABEL'..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
		kubectl apply -f k8s/argocd/sealed-secrets-$$CLUSTER_LABEL-applicationset.yaml && \
		kubectl apply -f k8s/argocd/cloudflare-tunnel-$$CLUSTER_LABEL-applicationset.yaml && \
		kubectl apply -f k8s/argocd/diocesan-vitality-$$CLUSTER_LABEL-applicationset.yaml
	@echo "✅ Step 4 Complete: ApplicationSets installed for $$CLUSTER_LABEL"

sealed-secrets-create: ## Step 5: Create tunnel token sealed secret (usage: make sealed-secrets-create CLUSTER_LABEL=dev)
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	echo "🚀 Step 5: Creating tunnel token sealed secret for '$$CLUSTER_LABEL'..." && \
	if [ "$$CLUSTER_LABEL" = "stg" ]; then ENV_DIR="staging"; else ENV_DIR="$$CLUSTER_LABEL"; fi && \
	echo "🔍 Extracting tunnel credentials from Terraform k8s-secrets..." && \
	cd terraform/environments/$$ENV_DIR && \
	CREDENTIALS_FILE="k8s-secrets/cloudflare-tunnel-$$ENV_DIR.yaml" && \
	if [ ! -f "$$CREDENTIALS_FILE" ]; then \
		echo "❌ Could not find tunnel credentials file: $$CREDENTIALS_FILE"; \
		echo "💡 Ensure tunnel has been created: make tunnel-create CLUSTER_LABEL=$$CLUSTER_LABEL"; \
		exit 1; \
	fi && \
	CREDENTIALS_B64=$$(grep "credentials.json" "$$CREDENTIALS_FILE" | cut -d'"' -f4) && \
	CREDENTIALS_JSON=$$(echo "$$CREDENTIALS_B64" | base64 -d) && \
	ACCOUNT_TAG=$$(echo "$$CREDENTIALS_JSON" | jq -r '.AccountTag') && \
	TUNNEL_ID=$$(echo "$$CREDENTIALS_JSON" | jq -r '.TunnelID') && \
	TUNNEL_SECRET=$$(echo "$$CREDENTIALS_JSON" | jq -r '.TunnelSecret') && \
	TUNNEL_SECRET_B64=$$(echo -n "$$TUNNEL_SECRET" | base64 -w0) && \
	TUNNEL_TOKEN=$$(echo "{\"a\":\"$$ACCOUNT_TAG\",\"t\":\"$$TUNNEL_ID\",\"s\":\"$$TUNNEL_SECRET_B64\"}" | base64 -w0) && \
	cd - >/dev/null && \
	if [ -z "$$TUNNEL_TOKEN" ] || [ -z "$$TUNNEL_ID" ]; then \
		echo "❌ Could not extract tunnel credentials"; \
		echo "💡 Ensure tunnel has been created: make tunnel-create CLUSTER_LABEL=$$CLUSTER_LABEL"; \
		exit 1; \
	fi && \
	echo "✅ Extracted tunnel ID: $$TUNNEL_ID" && \
	echo "✅ Generated tunnel token: $$(echo "$$TUNNEL_TOKEN" | cut -c1-20)..." && \
	kubectl config use-context do-nyc2-dv-$$CLUSTER_LABEL && \
	echo "🔧 Installing kubeseal CLI if needed..." && \
	$(MAKE) _install-kubeseal && \
	echo "⏳ Waiting for sealed-secrets controller to be ready..." && \
	kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=sealed-secrets -n kube-system --timeout=300s && \
	echo "🔐 Creating sealed secret from extracted tunnel token..." && \
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

_update-kustomization-for-sealed-secret: ## Update kustomization to use sealed secret instead of plain secret
	@CLUSTER_LABEL=$${CLUSTER_LABEL:-dev} && \
	KUSTOMIZATION_FILE="k8s/infrastructure/cloudflare-tunnel/environments/$$CLUSTER_LABEL/kustomization.yaml" && \
	echo "📝 Updating $$CLUSTER_LABEL kustomization to include sealed secret..." && \
	if ! grep -q "cloudflared-token-sealedsecret.yaml" $$KUSTOMIZATION_FILE 2>/dev/null; then \
		if [ ! -f $$KUSTOMIZATION_FILE ]; then \
			echo "apiVersion: kustomize.config.k8s.io/v1beta1" > $$KUSTOMIZATION_FILE && \
			echo "kind: Kustomization" >> $$KUSTOMIZATION_FILE && \
			echo "" >> $$KUSTOMIZATION_FILE && \
			echo "resources:" >> $$KUSTOMIZATION_FILE && \
			echo "  - ../../base" >> $$KUSTOMIZATION_FILE; \
		fi && \
		if ! grep -q "resources:" $$KUSTOMIZATION_FILE; then \
			echo "" >> $$KUSTOMIZATION_FILE && \
			echo "resources:" >> $$KUSTOMIZATION_FILE && \
			echo "  - ../../base" >> $$KUSTOMIZATION_FILE; \
		fi && \
		echo "  - cloudflared-token-sealedsecret.yaml" >> $$KUSTOMIZATION_FILE; \
	fi

argocd-password: ## Get ArgoCD admin password
	@echo "🔑 ArgoCD Admin Password:"
	@if [ -f .argocd-admin-password ]; then \
		cat .argocd-admin-password && echo; \
	else \
		kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d && echo || echo "❌ ArgoCD not installed or password not found"; \
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
