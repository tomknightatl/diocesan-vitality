# Infrastructure Setup Commands

Simple commands to set up the infrastructure in 4 steps.

## Prerequisites

Ensure `.env` file contains:
```
DIGITALOCEAN_TOKEN=<your_do_token>
CLOUDFLARE_API_TOKEN=<your_cf_token>
CLOUDFLARE_ACCOUNT_ID=<your_cf_account_id>
CLOUDFLARE_ZONE_ID=<your_cf_zone_id>
```

## Option A: Run All Steps at Once

```bash
make infra-setup
```

## Option B: Run Each Step Individually

```bash
# Step 1: Create cluster and kubectl context
make cluster-create

# Step 2: Install ArgoCD and configure repository
make argocd-install

# Step 3: Install ArgoCD ApplicationSets
make argocd-apps

# Step 4: Create Cloudflare tunnel and DNS records
make tunnel-create
```

## Cleanup

```bash
# Destroy everything
make infra-destroy

# Or destroy individual components
make tunnel-destroy
make argocd-destroy
make cluster-destroy
```

## Status Check

```bash
# Check overall infrastructure status
make infra-status
```