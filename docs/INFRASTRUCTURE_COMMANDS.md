# Infrastructure Setup Commands

Simple commands to set up the infrastructure in 4 steps.

## Prerequisites

Ensure `.env` file contains:
```
DIGITALOCEAN_TOKEN=<your_do_token>
CLOUDFLARE_API_TOKEN=<your_cf_token>
CLOUDFLARE_ACCOUNT_ID=<your_cf_account_id>
CLOUDFLARE_ZONE_ID=<your_cf_zone_id>

# ArgoCD Admin Passwords (one per environment)
ARGOCD_ADMIN_PASSWORD_DEV=<secure_password_for_dev>
ARGOCD_ADMIN_PASSWORD_STG=<secure_password_for_staging>
ARGOCD_ADMIN_PASSWORD_PRD=<secure_password_for_production>
```

## Option A: Run All Steps at Once

```bash
make infra-setup
```

## Option B: Run Each Step Individually

```bash
# Step 1: Create cluster and kubectl context
make cluster-create

# Step 2: Create Cloudflare tunnel and DNS records
make tunnel-create

# Step 3: Install ArgoCD and configure repository
make argocd-install

# Step 4: Install ArgoCD ApplicationSets
make argocd-apps
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

# Get ArgoCD admin password
make argocd-password
```

## ArgoCD Password Management

The system automatically:
1. Installs ArgoCD with a random initial password
2. Installs ArgoCD CLI if not present
3. Logs in with the initial password
4. Changes the password to your custom password from `.env`
5. Saves the custom password to `.argocd-admin-password`

**Environment-specific passwords:**
- `ARGOCD_ADMIN_PASSWORD_DEV` - Development environment
- `ARGOCD_ADMIN_PASSWORD_STG` - Staging environment  
- `ARGOCD_ADMIN_PASSWORD_PRD` - Production environment

If no custom password is found in `.env`, the initial random password is preserved.