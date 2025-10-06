# Infrastructure Setup Commands

Simple commands to set up the infrastructure in 5 steps.

## Environment Naming Reference

All infrastructure commands use standardized naming across the stack:

| Environment | Make Variable       | Cluster Name | kubectl Context  | Namespace                   | ArgoCD URL                              |
| ----------- | ------------------- | ------------ | ---------------- | --------------------------- | --------------------------------------- |
| Development | `CLUSTER_LABEL=dev` | `dv-dev`     | `do-nyc2-dv-dev` | `diocesan-vitality-dev`     | https://dev.argocd.diocesanvitality.org |
| Staging     | `CLUSTER_LABEL=stg` | `dv-stg`     | `do-nyc2-dv-stg` | `diocesan-vitality-staging` | https://stg.argocd.diocesanvitality.org |
| Production  | `CLUSTER_LABEL=prd` | `dv-prd`     | `do-nyc2-dv-prd` | `diocesan-vitality`         | https://prd.argocd.diocesanvitality.org |

**Example**: `make cluster-create CLUSTER_LABEL=dev` creates cluster `dv-dev` with context `do-nyc2-dv-dev`

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
# For development environment (default)
make infra-setup

# For staging environment
make infra-setup CLUSTER_LABEL=stg

# For production environment
make infra-setup CLUSTER_LABEL=prd
```

## Option B: Run Each Step Individually

```bash
# Step 1: Create cluster and kubectl context
make cluster-create CLUSTER_LABEL=dev

# Step 2: Create Cloudflare tunnel and DNS records
make tunnel-create CLUSTER_LABEL=dev

# Step 3: Install ArgoCD and configure repository
make argocd-install CLUSTER_LABEL=dev

# Step 4: Install ArgoCD ApplicationSets
make argocd-apps CLUSTER_LABEL=dev

# Step 5: Convert tunnel credentials to sealed secrets
make sealed-secrets-create CLUSTER_LABEL=dev
```

## Environment-Specific Deployment

The system now supports environment-specific deployments:

- **CLUSTER_LABEL=dev**: Development environment
- **CLUSTER_LABEL=stg**: Staging environment
- **CLUSTER_LABEL=prd**: Production environment

Each environment:

- Creates a cluster with proper labeling
- Deploys only applications targeting that environment
- Uses environment-specific ArgoCD passwords
- Applies correct ApplicationSets for the cluster type

## Step 5: Sealed Secrets (Security)

Step 5 creates secure sealed secrets for Cloudflare tunnel authentication using tokens from the Cloudflare Web UI:

**What it does:**

1. Waits for sealed-secrets controller to be ready (deployed in Step 4)
2. Uses tunnel token from Cloudflare Web UI (not credentials.json)
3. Creates a sealed secret using `kubeseal` CLI with correct kubectl context
4. Commits and pushes the sealed secret to the repository
5. Waits for the tunnel application to sync and become healthy

**Security Benefits:**

- Tunnel tokens are encrypted and safe to store in Git
- Only the target cluster can decrypt the sealed secret
- Follows GitOps principles - all configuration in repository
- Uses Cloudflare's recommended token-based authentication

**Requirements:**

- `kubeseal` CLI must be installed
- Sealed-secrets controller must be running (automatic after Step 4)
- Git repository access for committing sealed secrets
- Fresh tunnel token from Cloudflare Web UI

**Troubleshooting Step 5:**
If tunnel pods show `CrashLoopBackOff` or authentication errors:

1. **Get fresh token from Cloudflare Web UI:**

   ```bash
   # Navigate to Cloudflare Dashboard > Zero Trust > Networks > Tunnels
   # Click your tunnel > Configure > Copy the token from the Docker command
   ```

2. **Create sealed secret manually:**

   ```bash
   # Ensure correct kubectl context
   kubectl config use-context do-nyc2-dv-dev

   # Create sealed secret (replace TOKEN with actual token)
   echo -n "TOKEN_HERE" | kubectl create secret generic cloudflared-token \
     --dry-run=client --from-file=tunnel-token=/dev/stdin \
     --namespace=cloudflare-tunnel-dev -o yaml | \
     kubeseal -o yaml --namespace=cloudflare-tunnel-dev > \
     k8s/infrastructure/cloudflare-tunnel/environments/dev/cloudflared-token-sealedsecret.yaml

   # Commit and push
   git add k8s/infrastructure/cloudflare-tunnel/environments/dev/
   git commit -m "Update tunnel token sealed secret"
   git push
   ```

3. **Common fixes applied:**
   - Switched from QUIC to HTTP/2 transport (resolves UDP buffer issues)
   - Reduced resource limits for small clusters
   - Removed config file dependencies (uses token-only approach)
   - Applied proper security context with NET_ADMIN capability

## Cluster Scaling Commands

Scale node pools to zero to save costs when clusters are not in use, or restore them to normal size.

### Scale to Zero (Cost Savings)

```bash
# Scale individual clusters to zero nodes
make cluster-scale-dev-0     # Development: 3 nodes → 0 nodes
make cluster-scale-stg-0     # Staging: 3 nodes → 0 nodes
make cluster-scale-prd-0     # Production: 3 nodes → 0 nodes (requires confirmation)

# Scale all clusters to zero
make cluster-scale-all-0     # All environments → 0 nodes (requires confirmation)
```

### Restore to Normal Size

```bash
# Restore individual clusters to normal size (1 slow-pool + 2 fast-pool)
make cluster-scale-dev-normal     # Development: 0 → 3 nodes (1 slow + 2 fast)
make cluster-scale-stg-normal     # Staging: 0 → 3 nodes (1 slow + 2 fast)
make cluster-scale-prd-normal     # Production: 0 → 3 nodes (1 slow + 2 fast)

# Restore all clusters to normal size
make cluster-scale-all-normal     # All environments → 3 nodes each
```

**Notes:**

- Scaling to zero saves ~$36/month per cluster (DigitalOcean charges for nodes, not control plane)
- Node provisioning takes 2-3 minutes when restoring from zero
- Production scaling requires manual confirmation for safety
- Pods will automatically reschedule when nodes become available

## Cleanup

```bash
# Destroy everything for development (default)
make infra-destroy

# Destroy everything for staging
make infra-destroy CLUSTER_LABEL=stg

# Destroy everything for production
make infra-destroy CLUSTER_LABEL=prd

# Or destroy individual components
make tunnel-destroy CLUSTER_LABEL=dev
make argocd-destroy CLUSTER_LABEL=dev
make cluster-destroy CLUSTER_LABEL=dev
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
