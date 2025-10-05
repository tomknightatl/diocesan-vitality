# Dev: more frequent checks for faster feedback
livenessProbe:
  periodSeconds: 15

# Prd: less frequent, more stable
livenessProbe:
  periodSeconds: 60
  failureThreshold: 10# Cloudflare Tunnel ApplicationSet Configuration

## Repository Structure

The following files are included in your repository:

```

   📁 infra/
    └── 📁 Diocesan Vitality/
        └── 📁 k8s/
            └── 📁 argocd/
                ├── 📁 cloudflare-tunnel/
                │   ├── 📁 base/                          ← Common resources
                │   │   ├── 📄 deployment.yaml
                │   │   ├── 📄 service.yaml
                │   │   ├── 📄 namespace.yaml
                │   │   ├── 📄 pod-disruption-budget.yaml
                │   │   ├── 📄 kustomization.yaml
                │   │   └── 📄 tunnel-token-template.yaml
                │   ├── 📁 overlays/
                │   │   ├── 📁 dev/                       ← Dev-specific config
                │   │   │   ├── 📄 cloudflared-config.yaml    ← Dev tunnel ID & hostnames
                │   │   │   ├── 📄 sealedsecret.yaml          ← Dev tunnel token
                │   │   │   ├── 📄 resource-limits.yaml       ← Dev resource constraints
                │   │   │   └── 📄 kustomization.yaml
                │   │   ├── 📁 stg/                       ← Staging-specific config
                │   │   │   ├── 📄 cloudflared-config.yaml    ← Staging tunnel ID & hostnames
                │   │   │   ├── 📄 sealedsecret.yaml          ← Staging tunnel token
                │   │   │   ├── 📄 resource-limits.yaml       ← Staging resource constraints
                │   │   │   └── 📄 kustomization.yaml
                │   │   ├── 📁 prd/                       ← Prod-specific config
                │   │   │   ├── 📄 cloudflared-config.yaml    ← Prod tunnel ID & hostnames
                │   │   │   ├── 📄 sealedsecret.yaml          ← Prod tunnel token
                │   │   │   ├── 📄 resource-limits.yaml       ← Prod resource constraints
                │   │   │   └── 📄 kustomization.yaml
                │   │   └── 📁 arg/                       ← ArgoCD cluster config
                │   │       ├── 📄 cloudflared-config.yaml    ← ArgoCD tunnel ID & hostnames
                │   │       ├── 📄 sealedsecret.yaml          ← ArgoCD tunnel token
                │   │       ├── 📄 resource-limits.yaml       ← ArgoCD resource constraints
                │   │       └── 📄 kustomization.yaml
                ├── 📄 cloudflare-tunnel-applicationset.yaml  ← Multi-environment ApplicationSet
                ├── 📄 cloudflare-tunnel-applicationset-README.md
                └── 📄 README.md
```

## ApplicationSet Configuration

The ApplicationSet YAML file (`cloudflare-tunnel-applicationset.yaml`) is configured to deploy Cloudflare tunnel to multiple environments using Kustomize overlays for environment-specific configuration.

**Key Features:**
- **Multi-Environment Support**: Deploys to dev, stg, prd, and arg environments
- **Environment-Specific Configuration**: Each environment has its own tunnel ID, token, and hostnames
- **Environment-Specific Resources**: Each environment has optimized resource allocation
- **Kustomize Overlays**: Uses overlays pattern for environment-specific customization
- **Auto-Sync**: Automatically syncs changes from Git
- **Pre-configured**: Repository URL already set to `https://github.com/optinosis/optinosis.git`
- **Secure**: Uses SealedSecrets for tunnel token storage per environment

## Resource Allocation Strategy

Each environment uses optimized resource allocation based on its purpose.

The ApplicationSet now supports multiple environments with environment-specific configurations:
- **Dev**: Uses `overlays/dev/` with dev-specific tunnel ID, hostnames, and minimal resources
- **Stg**: Uses `overlays/stg/` with stg-specific tunnel ID, hostnames, and moderate resources
- **Prd**: Uses `overlays/prd/` with prd-specific tunnel ID, hostnames, and production-grade resources
- **Arg**: Uses `overlays/arg/` with ArgoCD-specific tunnel ID, hostnames, and management-appropriate resources
- **Environment Isolation**: Each environment has its own sealed secret, tunnel configuration, and resource allocation

### 📁 **Kustomize Overlay Structure**
- Common resources in `base/` directory (deployment, service, namespace, etc.)
- Environment-specific configs in `overlays/{environment}/` directories
- Each overlay contains its own tunnel ID, hostnames, sealed secret, and resource limits
- Follows GitOps best practices for multi-environment deployments

### 🔧 **Environment-Specific Resource Management**
- **Dev Environment**: Minimal resources (50m CPU, 128Mi memory) for resource-constrained clusters
- **Staging Environment**: Moderate resources (100m CPU, 256Mi memory) for testing workloads
- **Production Environment**: Production-grade resources (200m CPU, 256Mi memory) with high availability
- **Resource Patches**: Uses Kustomize strategic merge patches for environment-specific resource allocation

### 🔄 **GitOps Integration**
- **Auto-Sync**: Automatically syncs changes from Git
- **Self-Healing**: Automatically corrects configuration drift
- **Namespace Creation**: Automatically creates the `cloudflare-tunnel` namespace

## Deploying Cloudflare Tunnel with GitOps

This repository contains the configuration for deploying a Cloudflare tunnel using GitOps principles with ArgoCD and SealedSecrets to securely expose:

- ArgoCD UI at https://argocd.domainname.com

## Prerequisites

- ArgoCD installed and configured
- `kubeseal` CLI tool installed
- Cloudflare account with access to create tunnels
- Access to your GitHub repository
- SealedSecrets controller running in the kube-system namespace

## Implementation Steps

### Step 1: Label Your Clusters if they are not already labeled.

Those instructions are in the ~/Diocesan Vitality/k8s/argocd/README.md file


### Step 2: Apply the ApplicationSet

```bash
# Apply the ApplicationSet to deploy Cloudflare tunnel
kubectl apply -f ~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel-applicationset.yaml
```

**Expected Status After Step 2**:
The Application will show as **Healthy** but **Degraded** with an error about the sealed secret: `Failed to unseal: no key could decrypt secret (tunnel-token)`. This is normal and expected because you haven't created the actual tunnel token yet. The Application will become fully healthy after completing Steps 4-7 below.

### Step 3: Create Environment-Specific Cloudflare Tunnels

Create separate tunnels for each environment to ensure proper isolation:

#### Dev Environment
1. In your Cloudflare dashboard, navigate to Zero Trust > Networks > Tunnels
2. Click "Create a tunnel"
3. Give your tunnel a name: "optinosis-cluster-dev"
4. Choose your environment (Docker is easiest for copying the token)
5. Copy the token - you'll need this for the sealed secret
6. Add public hostnames for dev:
    - Subdomain: argocd-optinosis-dev, Domain: optinosis.tech, URL: argocd-server.argocd.svc.cluster.local:80
    - Subdomain: kubeflow, Domain: optinosis.tech, URL: istio-ingressgateway.istio-system.svc.cluster.local:80
    - Subdomain: optinexus2, Domain: optinosis.tech, URL: open-webui.open-webui.svc.cluster.local:8080

#### Stg Environment (Optional)
1. Create another tunnel: "optinosis-cluster-stg"
2. Add stg-specific hostnames:
    - Subdomain: argocd-optinosis-stg, Domain: optinosis.tech
    - Subdomain: kubeflow-stg, Domain: optinosis.tech
    - Subdomain: optinexus2-stg, Domain: optinosis.tech

#### Prd Environment (Optional)
1. Create another tunnel: "optinosis-cluster-prd"
2. Add prd hostnames:
    - Subdomain: argocd-optinosis, Domain: optinosis.tech
    - Subdomain: kubeflow, Domain: optinosis.tech
    - Subdomain: optinexus2, Domain: optinosis.tech

#### Arg Environment (ArgoCD Management)
1. Create another tunnel: "optinosis-cluster-arg"
2. Add ArgoCD management hostnames:
    - Subdomain: argocd-arg, Domain: optinosis.tech
    - Subdomain: grafana-arg, Domain: optinosis.tech (if monitoring is deployed)
    - Subdomain: prometheus-arg, Domain: optinosis.tech (if monitoring is deployed)

### Step 4: Create Cloudflare Applications for Each Environment

Create separate Cloudflare Access applications for each environment:

#### Dev Environment
1. Open Cloudflare > Access > Applications
2. Click "Create Application"
3. Enter:
   - Application name: "Optinexus2 Dev"
   - Subdomain: optinexus2
   - Domain: optinosis.tech
4. Click "Select existing policies"
5. Check the box for "Allow @optinosis.com email addresses" and click "Confirm"

#### Stg/Prd/Arg (Optional)
Repeat the above process for stg, prd, and arg with appropriate naming:
- "Optinexus2 Stg" → optinexus2-stg.optinosis.tech
- "Optinexus2 Prd" → optinexus2.optinosis.tech
- "ArgoCD Management" → argocd-arg.optinosis.tech

### Step 5: Create Environment-Specific SealedSecrets

Create sealed secrets for each environment's tunnel token:

**Important Context Note**:
- The `kubectl create secret` command can be run from any context since it uses `--dry-run=client` (no cluster interaction)
- The `kubeseal` command **must** be run with your kubectl context set to the **destination cluster** (where the tunnel will be deployed), not the ArgoCD server cluster, because kubeseal needs to communicate with the SealedSecrets controller running on the destination cluster

#### For Dev Environment

1. **Set your kubectl context to the dev cluster**

   ```bash
   # Set context to the dev cluster where the tunnel will be deployed
   kubectl config use-context do-nyc2-optinosis-cluster-dev

   # Verify you're in the correct context
   kubectl config current-context
   ```

2. **Save your prd tunnel token to a file**

   ```bash
   cd ~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/prd
   echo "your-dev-tunnel-token-here" > tunnel-token.txt
   ```
   Replace `your-dev-tunnel-token-here` with the actual token from your dev tunnel.

3. **Create a Kubernetes secret file**

   ```bash
   # This command works from any context since it's --dry-run=client
   kubectl create secret generic cloudflared-token \
     --namespace=cloudflare-tunnel \
     --from-file=tunnel-token=tunnel-token.txt \
     --dry-run=client \
     -o yaml > secret.yaml
   ```

4. **Seal the secret using kubeseal**

   ```bash
   # IMPORTANT: Make sure you're still in the prd cluster context
   # kubeseal connects to the SealedSecrets controller on the destination cluster
   kubeseal \
     --controller-namespace=kube-system \
     --controller-name=sealed-secrets-controller \
     --format yaml \
     < secret.yaml > sealed-secret.yaml
   ```

5. **Update your repository**

   Replace the content in `~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/prd/sealedsecret.yaml` with the content of your newly created `sealed-secret.yaml`.

6. **Update the tunnel ID in the config**

   Edit `~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/dev/cloudflared-config.yaml` to include your dev tunnel ID (you can find this in the Cloudflare dashboard).

7. **Clean up**

   ```bash
   rm tunnel-token.txt secret.yaml sealed-secret.yaml
   ```

#### For Stg/Dev/Arg (Optional)

Repeat the above process for each additional environment:
- Switch to the appropriate cluster context
- Create the sealed secret in the corresponding overlay directory
- Update the tunnel ID in that environment's config file

### Step 6: Create Environment-Specific Resource Configuration

The repository now includes environment-specific resource limits to optimize deployment for each environment's constraints:


### Step 8: Push the Sealed Secret to Your GitHub Repository

1. Update the files in your repository:

   ```bash
   git status   # confirm overlay files have changed
   git switch -c feature/multi-env-cloudflare-tunnel-with-resources
   git add ~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/
   git commit -m "Add multi-environment Cloudflare tunnel with environment-specific resources
   - Use Kustomize strategic merge patches for resource customization
   - Environment-specific resources (dev, stg, arg, prd)"

   git push -u origin feature/multi-env-cloudflare-tunnel-with-resources
   ```

2. Create a pull request

3. Merge the pull request

### Step 9: Verify the Deployment

```bash
# Check if the ApplicationSet was created
kubectl get applicationsets -n argocd | grep cloudflare-tunnel

# Check if applications were generated
kubectl get applications -n argocd | grep cloudflare-tunnel

# Monitor the application status
kubectl get application cloudflare-tunnel-optinosis-cluster-prd -n argocd -o jsonpath='{.status.sync.status}'

# Check detailed application status
kubectl describe application cloudflare-tunnel-optinosis-cluster-dev -n argocd
```

### Step 10: Verify the Cloudflare Tunnel Deployment

1. Check that the ArgoCD application has synced:

   ```bash
   kubectl get application cloudflare-tunnel-optinosis-cluster-dev -n argocd
   ```

2. Verify the Cloudflare tunnel pods are running with correct resources:

   ```bash
   kubectl get pods -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev
   kubectl describe pods -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev
   ```

3. Check the logs to ensure the tunnel is connected:

   ```bash
   kubectl logs -n cloudflare-tunnel -l app=cloudflared --context=do-nyc2-optinosis-cluster-dev
   ```

4. Verify resource allocation:

   ```bash
   kubectl top pods -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev
   ```

5. Test connectivity through the tunnel:

   ```bash
   curl -v https://optinexus2.optinosis.tech
   ```

## Resource Management Benefits

### Environment-Specific Optimization
- **Dev**: Minimal resource footprint (50m CPU, 128Mi memory) for resource-constrained development clusters
- **Stg**: Balanced resources (100m CPU, 256Mi memory) for realistic testing scenarios
- **Prd**: Production-grade resources (200m CPU, 256Mi memory) with high availability
- **Arg**: Management-appropriate resources (100m CPU, 256Mi memory) for ArgoCD and monitoring tools

### Cluster Resource Efficiency
- **Prevents FailedScheduling**: Resources tuned to cluster capacity
- **Cost Optimization**: Right-sizing resources per environment purpose
- **Scalability**: Easy to adjust resources as needs evolve

### High Availability Strategy
- **Dev**: Single replica for simplicity and resource conservation
- **Stg**: Two replicas for testing failover scenarios
- **Prd**: Three replicas for maximum availability
- **Arg**: Two replicas for management cluster reliability

## Optimizing Cloudflare Tunnel Performance

For optimal tunnel performance and stability, we use the following configuration:

1. **ConfigMap for advanced settings**: Using a ConfigMap with a `config.yaml` file allows for more detailed configuration, and contains a list of Domain Names:

      > **Important**: Ensure the tunnel ID in the ConfigMap matches the tunnel ID associated with your token. You can find this ID in the Cloudflare dashboard or in the logs when the tunnel connects.

2. **Environment-Specific Resource Allocation**: Each environment has optimized resource allocation:

   ```yaml
   # Dev Environment
   resources:
     limits:
       cpu: 200m
       memory: 256Mi
     requests:
       cpu: 50m
       memory: 128Mi

   # Prd Environment
   resources:
     limits:
       cpu: 1000m
       memory: 1Gi
     requests:
       cpu: 200m
       memory: 256Mi
   ```

3. **Properly Configured Health Probes**: Adjust liveness and readiness probes for reliability:

   ```yaml
   livenessProbe:
     httpGet:
       path: /ready
       port: 2000
     failureThreshold: 5
     initialDelaySeconds: 60
     periodSeconds: 30
     timeoutSeconds: 10
   ```

### Configuration Management

### Updating Configuration

To update Cloudflare tunnel configuration for a specific environment:

1. **Edit environment-specific files**: Modify files in `~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/{environment}/`
2. **Commit changes**: `git add` and `git commit` the changes
3. **Push to repository**: `git push origin main`
4. **ArgoCD auto-sync**: ApplicationSet will automatically detect and apply changes

### Example Configuration Updates

```yaml
# To update the dev tunnel configuration:
# Edit ~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/dev/cloudflared-config.yaml

# Add new hostnames or modify existing ones
ingress:
  - hostname: new-service-dev.optinosis.tech
    service: http://new-service.default.svc.cluster.local:80

# To update dev resources:
# Edit ~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/dev/resource-limits.yaml

# To update stg configuration:
# Edit ~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/stg/cloudflared-config.yaml

# Prd updates:
# Edit ~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/prd/cloudflared-config.yaml

# Arg updates:
# Edit ~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/arg/cloudflared-config.yaml
```

### Environment-Specific Customization

Each environment can have different:
- **Tunnel IDs**: Separate Cloudflare tunnels per environment
- **Hostnames**: Environment-specific subdomain patterns
- **Log Levels**: Different logging verbosity per environment
- **Resource Limits**: Environment-appropriate resource allocation (optimized for cluster capacity)
- **Replica Counts**: Environment-specific availability requirements
- **Service URLs**: Environment-specific backend service addresses

## Dev-Focused Deployment

This ApplicationSet supports multiple environments with environment-specific features:

### Dev Environment Features:
- **Dev Labels**: Targets clusters labeled with `environment: dev`
- **Dev-specific Hostnames**: Uses `-dev` suffix for dev services
- **Dev Tunnel**: Isolated tunnel instance for dev workloads
- **Resource Efficient**: Minimal resource requests (50m CPU, 128Mi memory) for resource-constrained clusters
- **Single Replica**: Simplified deployment for development purposes
- **Security Focused**: Uses SealedSecrets for secure token management

### Stg Environment Features (Optional):
- **Stg Labels**: Targets clusters labeled with `environment: stg`
- **Stg Hostnames**: Uses `-stg` suffix for stg services
- **Stg Tunnel**: Separate tunnel instance for stg validation
- **Moderate Resources**: Balanced resource allocation (100m CPU, 256Mi memory)
- **Dual Replicas**: Testing high availability scenarios

### Prd Environment Features (Optional):
- **Prd Labels**: Targets clusters labeled with `environment: prd`
- **Prd Hostnames**: Uses clean hostnames for prd services
- **Prd Tunnel**: Dedicated tunnel instance for prd workloads
- **Prd Resources**: Production-grade resource allocation (200m CPU, 256Mi memory)
- **High Availability**: Three replicas for maximum availability

### Arg Environment Features (ArgoCD Management):
- **Arg Labels**: Targets clusters labeled with `environment: arg`
- **Arg Hostnames**: Uses `-arg` suffix for management services
- **Arg Tunnel**: Dedicated tunnel instance for ArgoCD and monitoring workloads
- **Management Resources**: Balanced resource allocation (100m CPU, 256Mi memory)
- **Dual Replicas**: Reliable access to management tools

## Multi-Environment Setup

This configuration supports multiple environments out of the box:

### Directory Structure
```
cloudflare-tunnel/
├── base/                    ← Common resources (deployment, service, etc.)
├── overlays/
│   ├── dev/                 ← Dev tunnel ID, token, hostnames, resources
│   ├── stg/                 ← Stg tunnel ID, token, hostnames, resources
│   ├── prd/                 ← Prd tunnel ID, token, hostnames, resources
│   └── arg/                 ← Arg tunnel ID, token, hostnames, resources
```

### Adding New Environments

To add a new environment (e.g., arg):

1. **Create the overlay directory**:
   ```bash
   mkdir -p ~/Diocesan Vitality/k8s/argocd/cloudflare-tunnel/overlays/arg
   ```

2. **Create arg-specific files**:
   - `kustomization.yaml` (referencing base and including resource patch)
   - `cloudflared-config.yaml` (with arg tunnel ID and hostnames)
   - `sealedsecret.yaml` (with arg tunnel token)
   - `resource-limits.yaml` (with arg-appropriate resource allocation)

3. **Label the arg cluster**:
   ```bash
   kubectl label secret optinosis-cluster-arg-secret -n argocd environment=arg
   ```

4. **ApplicationSet automatically deploys** to arg

### Environment Isolation Benefits

- **Separate Tunnel IDs**: Each environment uses its own Cloudflare tunnel
- **Independent Tokens**: Each environment has its own sealed secret
- **Custom Hostnames**: Environment-specific subdomain patterns (e.g., `-dev`, `-stg`)
- **Optimized Resources**: Each environment has resource allocation tuned to its purpose and cluster capacity
- **Isolated Configuration**: Changes to one environment don't affect others

## Troubleshooting

If the tunnel is not working:

1. **Check ApplicationSet events**:
   ```bash
   kubectl describe applicationset cloudflare-tunnel-dev -n argocd
   ```

2. **Check application sync status**:
   ```bash
   kubectl get application cloudflare-tunnel-optinosis-cluster-dev -n argocd -o yaml
   ```

3. **Check for resource scheduling issues**:
   ```bash
   kubectl describe pods -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev
   kubectl get events -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev
   ```

4. **Check the logs of the Cloudflare tunnel pods**:
   ```bash
   kubectl logs -n cloudflare-tunnel -l app=cloudflared --context=do-nyc2-optinosis-cluster-dev
   ```

5. **Verify resource allocation**:
   ```bash
   kubectl top nodes --context=do-nyc2-optinosis-cluster-dev
   kubectl top pods -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev
   ```

6. **Verify the sealed secret was properly decrypted**:
   ```bash
   kubectl get secret -n cloudflare-tunnel cloudflared-token -o yaml --context=do-nyc2-optinosis-cluster-dev
   ```

7. **Check the status of your tunnel in the Cloudflare dashboard**:
   ```
   Zero Trust > Networks > Tunnels > Select your tunnel
   ```

8. **Verify the tunnel is connected**:
   ```bash
   kubectl exec -n cloudflare-tunnel deploy/cloudflared --context=do-nyc2-optinosis-cluster-dev -- cloudflared tunnel info
   ```

9. **If you see "Unauthorized: Failed to get tunnel" errors**:
   - Ensure the tunnel ID in your ConfigMap matches the tunnel ID associated with your token
   - Consider regenerating a new tunnel token in the Cloudflare dashboard
   - Verify the token is properly mounted in the pod

10. **If you see FailedScheduling events**:
    - Check if resources are too high for your cluster capacity
    - Consider reducing resource requests in the environment's `resource-limits.yaml`
    - Verify node capacity: `kubectl describe nodes --context=do-nyc2-optinosis-cluster-dev`

11. **Restart the tunnel pods if needed**:
    ```bash
    kubectl rollout restart -n cloudflare-tunnel deployment/cloudflared --context=do-nyc2-optinosis-cluster-dev
    ```

12. **If the tunnel connects but terminates after a short period** (look for "Application error 0x0" in logs):
    - Increase CPU and memory resources in the environment's `resource-limits.yaml`
    - Adjust probe timeouts and failure thresholds
    - Use a specific Cloudflare image version rather than "latest"
    - Add a termination grace period to the pod specification

13. **Check connectivity to your origin services**:
    ```bash
    # Test from inside the pod
    kubectl exec -n cloudflare-tunnel $(kubectl get pods -n cloudflare-tunnel -l app=cloudflared -o jsonpath='{.items[0].metadata.name}' --context=do-nyc2-optinosis-cluster-dev) --context=do-nyc2-optinosis-cluster-dev -- curl -v http://argocd-server.argocd.svc.cluster.local:80
    ```

14. **If you encounter issues with kubeseal**:
    ```bash
    # Check where your sealed-secrets controller is running
    kubectl get pods -A | grep sealed-secrets

    # Verify the service name
    kubectl get svc -n kube-system | grep sealed-secrets

    # Make sure you're using the correct namespace and name in your kubeseal command
    ```

## Expected Results

After successful deployment across environments:
- ✅ ApplicationSet `cloudflare-tunnel-multi-env` created in ArgoCD
- ✅ Applications generated per environment: `cloudflare-tunnel-{cluster-name}`
- ✅ `cloudflare-tunnel` namespace created on each target cluster
- ✅ Environment-specific Cloudflare tunnel pods running and healthy with appropriate resources
- ✅ Tunnels connected to Cloudflare edge network per environment
- ✅ ArgoCD, Kubeflow, and Open WebUI services accessible via environment-specific URLs
- ✅ Configuration managed through Kustomize overlays per environment
- ✅ Resource allocation optimized per environment

### Example URLs by Environment:

**Dev:**
- https://argocd-optinosis-dev.optinosis.tech
- https://kubeflow.optinosis.tech
- https://optinexus2.optinosis.tech

**Stg (Optional):**
- https://argocd-optinosis-stg.optinosis.tech
- https://kubeflow-stg.optinosis.tech
- https://optinexus2-stg.optinosis.tech

**Prd (Optional):**
- https://argocd-optinosis.optinosis.tech
- https://kubeflow.optinosis.tech
- https://optinexus2.optinosis.tech

**Arg (ArgoCD Management):**
- https://argocd-arg.optinosis.tech
- https://grafana-arg.optinosis.tech (if monitoring deployed)
- https://prometheus-arg.optinosis.tech (if monitoring deployed)

## GitOps Benefits

This enhanced configuration follows GitOps principles by:
- 🔄 **Declarative**: All configuration in version-controlled YAML files
- 📦 **Versioned**: All changes tracked in Git
- 🚀 **Automated**: Auto-sync enabled with self-healing
- 🎯 **Selective**: Deploys only to properly labeled dev clusters
- 🔍 **Observable**: Full visibility through ArgoCD UI
- 🛠️ **Maintainable**: Configuration separate from deployment logic
- 🔒 **Secure**: Uses SealedSecrets for sensitive data
- 🌍 **Multi-Environment Ready**: Supports dev, stg, prd, and arg deployments
- 🔒 **Environment Isolation**: Each environment uses separate tunnels, tokens, hostnames, and resource allocation
- ⚡ **Resource Optimized**: Environment-specific resource allocation prevents scheduling issues

## Security Benefits of SealedSecrets

### Why Use SealedSecrets for Tunnel Tokens?

1. **Git-Safe Secrets**: Store encrypted tunnel tokens in Git repositories safely
2. **Cluster-Specific Encryption**: Tokens can only be decrypted in the target cluster
3. **GitOps Compatible**: Fits perfectly with GitOps workflows
4. **Namespace Scoped**: Secrets are encrypted for specific namespaces
5. **Asymmetric Encryption**: Uses public-key cryptography for security

### Security Model

- **Public Key**: Used by `kubeseal` to encrypt secrets (can be shared)
- **Private Key**: Stays in the cluster, used by controller to decrypt
- **Scope Control**: Secrets bound to specific cluster/namespace/name combinations

Your tunnel should now be operational and routing traffic to your ArgoCD, Kubeflow, and Open WebUI services across all configured environments!

## Migration from Single Environment

If you're migrating from a single environment setup:

1. **Create the new overlay structure** as described above
2. **Move existing files** to `overlays/dev/`
3. **Create base directory** with common resources
4. **Add resource limits** per environment
5. **Update ApplicationSet** to use the multi-environment version
6. **Test thoroughly** in dev before adding staging/production

This architecture provides a solid foundation for scaling your Cloudflare tunnel deployment across multiple environments while maintaining security and operational best practices.

## Advanced Configuration Options

### Custom Resource Limits per Environment

You can customize resource allocation per environment by editing the `resource-limits.yaml` files:

```yaml
# overlays/prd/resource-limits.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflared
  namespace: cloudflare-tunnel
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: cloudflared
        resources:
          requests:
            cpu: 200m      # Production-level requests
            memory: 256Mi
          limits:
            cpu: 1000m     # High limits for prd
            memory: 1Gi
```

### Environment-Specific Logging

Different environments can have different log levels in their `cloudflared-config.yaml`:

```yaml
# Dev: debug logging
loglevel: debug

# Stg: info logging
loglevel: info

# Prd: warn logging
loglevel: warn
```

### Health Check Customization

Adjust health check intervals per environment by adding patches:

```yaml
# Dev: more frequent checks for faster feedback
livenessProbe:
  periodSeconds: 15

# Production: less frequent, more stable
livenessProbe:
  periodSeconds: 60
  failureThreshold: 10
```

### Replica Scaling Strategy

Scale replicas based on environment requirements:

```yaml
# Dev: single replica for resource efficiency
replicas: 1

# Stg: dual replicas for HA testing
replicas: 2

# Prd: three replicas for maximum availability
replicas: 3
```

## Security Considerations

### Tunnel Token Security

- **Environment Isolation**: Each environment uses its own tunnel token
- **Sealed Secrets**: Tokens encrypted per cluster using cluster-specific keys
- **Token Rotation**: Easy to rotate tokens per environment without affecting others
- **Least Privilege**: Each tunnel only has access to its environment's services

### Network Security

- **Internal Services Only**: All origin services use internal cluster DNS names
- **No Direct Exposure**: Services aren't directly exposed outside the cluster
- **TLS Termination**: Cloudflare handles TLS termination at the edge
- **Access Control**: Cloudflare Access provides additional authentication layer

### Git Security

- **No Plaintext Secrets**: All sensitive data encrypted before committing to Git
- **Environment Separation**: Clear separation of environment configs in Git
- **Audit Trail**: All changes tracked through Git commits
- **Pull Request Reviews**: Changes can be reviewed before deployment

## Monitoring and Observability

### Metrics Endpoint

Each tunnel pod exposes metrics on port 2000:

```bash
# Port forward to access metrics
kubectl port-forward svc/cloudflared 2000:2000 -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev

# Access metrics
curl http://localhost:2000/ready
curl http://localhost:2000/metrics
```

### Log Monitoring

Monitor tunnel health through logs:

```bash
# Follow logs for all tunnel pods
kubectl logs -f -n cloudflare-tunnel -l app=cloudflared --context=do-nyc2-optinosis-cluster-dev

# Check for specific error patterns
kubectl logs -n cloudflare-tunnel -l app=cloudflared --context=do-nyc2-optinosis-cluster-dev | grep -E "(ERR|WARN)"
```

### Resource Monitoring

Monitor resource usage across environments:

```bash
# Check node resource availability
kubectl top nodes --context=do-nyc2-optinosis-cluster-dev

# Monitor pod resource consumption
kubectl top pods -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev

# Check resource requests vs limits
kubectl describe pods -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev | grep -A 10 "Requests\|Limits"
```

### Tunnel Status in Cloudflare Dashboard

Monitor tunnel status directly in Cloudflare:
1. Navigate to Zero Trust > Networks > Tunnels
2. Check connection status for each environment's tunnel
3. Monitor traffic and error rates
4. Review analytics and performance metrics

## Performance Optimization

### Connection Tuning

For high-traffic environments, consider these optimizations:

```yaml
# Increase connection limits
proxy-connect-timeout: 60s
proxy-tls-timeout: 60s

# Enable compression
compression: true

# Optimize protocol
protocol: quic

# Connection pooling
originRequest:
  keepAliveConnections: 200
  keepAliveTimeout: 60s
```

### Resource Scaling Guidelines

**When to Scale Up Resources:**
- Pods getting OOMKilled (increase memory limits)
- High CPU throttling (increase CPU limits)
- Connection timeouts (increase both CPU and memory)
- Multiple FailedScheduling events (reduce requests or scale cluster)

**When to Scale Down Resources:**
- Consistently low resource utilization
- Cost optimization requirements
- Cluster resource constraints

**Scaling Example:**
```yaml
# If dev environment needs more resources:
# Edit overlays/dev/resource-limits.yaml
resources:
  requests:
    cpu: 100m      # Increased from 50m
    memory: 256Mi  # Increased from 128Mi
  limits:
    cpu: 500m      # Increased from 200m
    memory: 512Mi  # Increased from 256Mi
```

### Auto-Scaling Considerations

For prd environments, consider:
- **Horizontal Pod Autoscaler (HPA)**: Scale replicas based on CPU/memory usage
- **Vertical Pod Autoscaler (VPA)**: Automatically adjust resource requests
- **Cluster Autoscaler**: Scale cluster nodes based on pod resource requirements

## Troubleshooting Guide

### Common Issues by Environment

#### Dev Environment
- **Frequent restarts**: Usually due to resource constraints - increase resources in `resource-limits.yaml`
- **FailedScheduling**: Common in resource-constrained dev clusters - reduce resource requests
- **Connection timeouts**: Often backend services not ready - check service availability
- **Token issues**: Dev tokens may be regenerated frequently - verify sealed secret decryption

#### Staging Environment
- **Configuration drift**: Ensure staging mirrors production settings
- **Certificate issues**: Staging may use different certificates
- **Load testing impacts**: High load may cause temporary issues - monitor resource usage
- **Resource contention**: Multiple services competing for resources

#### Production Environment
- **Performance issues**: Monitor metrics and scale accordingly
- **Certificate expiration**: Monitor cert expiry dates
- **Traffic spikes**: Ensure adequate resources for peak load
- **High availability concerns**: Monitor replica health and distribution

### Debugging Steps by Issue Type

#### Resource Scheduling Issues
```bash
# Check pod events for scheduling failures
kubectl describe pods -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev

# Check node resource availability
kubectl describe nodes --context=do-nyc2-optinosis-cluster-dev

# Check resource requests vs cluster capacity
kubectl top nodes --context=do-nyc2-optinosis-cluster-dev
kubectl top pods --all-namespaces --context=do-nyc2-optinosis-cluster-dev

# Check for pending pods
kubectl get pods -n cloudflare-tunnel --context=do-nyc2-optinosis-cluster-dev | grep Pending
```

#### Tunnel Connection Issues
```bash
# Check tunnel registration
kubectl logs -n cloudflare-tunnel -l app=cloudflared | grep "Registered tunnel connection"

# Verify tunnel ID matches token
kubectl get configmap cloudflared-config -n cloudflare-tunnel -o yaml

# Check Cloudflare dashboard for tunnel status
```

#### Origin Service Unreachable
```bash
# Test service connectivity from within cluster
kubectl run debug-pod --image=busybox --rm -it -- sh
# From within pod:
wget -qO- http://open-webui.open-webui.svc.cluster.local:8080

# Check service endpoints
kubectl get endpoints -n open-webui
```

#### Authentication/Access Issues
```bash
# Verify Cloudflare Access policies
# Check browser developer tools for authentication errors
# Test with curl to see full response headers

curl -v https://optinexus2.optinosis.tech
```

### Emergency Procedures

#### Resource Exhaustion
1. **Immediate**: Scale down non-critical workloads
2. **Quick fix**: Reduce resource requests in `resource-limits.yaml`
3. **Long-term**: Scale cluster or optimize resource allocation

#### Tunnel Token Compromise
1. **Revoke token** in Cloudflare dashboard
2. **Generate new token** for affected environment
3. **Create new sealed secret** following Step 5 procedures
4. **Commit and push** updated sealed secret
5. **Verify tunnel reconnection** in logs

#### Service Outage
1. **Check tunnel pod status**: `kubectl get pods -n cloudflare-tunnel`
2. **Review recent changes**: Check Git commits and ArgoCD sync history
3. **Check resource issues**: `kubectl top nodes` and `kubectl describe pods`
4. **Rollback if needed**: Use ArgoCD to rollback to previous version
5. **Monitor recovery**: Watch logs and Cloudflare dashboard

#### Performance Degradation
1. **Check resource utilization**: `kubectl top pods -n cloudflare-tunnel`
2. **Review tunnel metrics**: Port-forward and check /metrics endpoint
3. **Scale resources**: Update overlay configuration if needed
4. **Monitor Cloudflare analytics**: Check tunnel performance in dashboard

This comprehensive multi-environment setup provides enterprise-grade tunnel management with proper security, monitoring, operational practices, and optimized resource allocation for each environment's specific needs.
