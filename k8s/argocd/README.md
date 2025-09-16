GitOps ApplicationSet Project
This folder contains the ArgoCD ApplicationSet configurations to deploy applications across multiple Kubernetes clusters using GitOps principles.

Repository Structure
Save the files in our GitHub repository in the following structure:

📁 optinosis (GitHub Repository)
│
└── 📁 infra/
    └── 📁 argocd/
        ├── 📄 bitnami-sealed-secrets-application-set-README.md 
        ├── 📄 bitnami-sealed-secrets-application-set.yaml 
        ├── 📁 bitnami-sealed-secrets
        │    ├── values-arg.yaml
        │    ├── values-dev.yaml
        │    ├── values-prd.yaml 
        │    └── values-stg.yaml               
        └── 📄 README.md                     ← This documentation
Additional Application Sets can be added with the same pattern.

## One-Time Setup
# Step 1: Install ArgoCD and Connect to This Repo

# Step 2: Create Kubernetes Secret(s) and  Label(s)

Cluster Secrets are automatically created when a cluster is added to ArgoCD.  However, no secret is created for the intial in-cluser cluster.  Run this command to create a secret for the in-cluster cluster:
kubectl create secret generic in-cluster-secret \
  -n argocd \
  --from-literal=name=in-cluster \
  --from-literal=server=https://kubernetes.default.svc \
  --from-literal=config='{}' \
  --dry-run=client -o yaml | kubectl apply -f -

# List all cluster secrets:
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=cluster --show-labels


# Label the in-cluster's secret with its environment-type-label

# Label the cluster(s), replacing <secret-name> and <environment-type-label> = {prd, dev, stg, etc.}.  A cluster can have no more than one environment-type-label.
kubectl label secret in-cluster-secret \
  -n argocd \
  argocd.argoproj.io/secret-type=cluster

kubectl label secret <secret-name> -n argocd environment=<environment-type-label>


# Verify the labels were applied
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=cluster --show-labels

# You should see one secret for each cluster, with environment=<environment-type-label>.  Example:
NAME                TYPE     DATA   AGE     LABELS
in-cluster-secret   Opaque   3      8m18s   argocd.argoproj.io/secret-type=cluster,environment=prd

## Deployment Instructions
# Step 3: Git Clone our Repo, which Creates Repository Structure
bash
git clone https://github.com/tomknightatl/infra.git   
cd infra

# Step 4: Apply the ApplicationSets directly, replacing <ApplicationSet.yaml> with its filename
bash
kubectl apply -f argocd/<ApplicationSet.yaml>

# Example ApplicationSets to deploy:
kubectl apply -f argocd/bitnami-sealed-secrets-application-set.yaml
kubectl apply -f argocd/cloudflare-tunnel-applicationset.yaml
kubectl apply -f argocd/metrics-server-application-set.yaml


# Step 5: Verify Deployment
Check that the ApplicationSets are running:

bash
# Check if ApplicationSets were created successfully
kubectl get applicationsets -n argocd

# Get detailed status of the ApplicationSets
kubectl describe applicationset <application-set-name> -n argocd

Verify that the ApplicationSets create Applications for clusters:

bash
# List all applications created by ApplicationSets
kubectl get applications -n argocd

# Check status of Applications
kubectl get applications -n argocd -o wide

bash
# Check sync status of all applications
kubectl get applications -n argocd -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status

# Watch application sync status in real-time
watch 'kubectl get applications -n argocd -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status'

# Get detailed sync information for troubleshooting
kubectl describe application <application-name> -n argocd

# Check application events for sync issues
kubectl get events -n argocd --field-selector involvedObject.kind=Application --sort-by='.lastTimestamp'