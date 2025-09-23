# Diocesan Vitality - Environment URLs

This document provides a comprehensive list of all service URLs across all environments.

## 🌐 Service URLs by Environment

### **Development Environment**
| Service | URL | Status | Notes |
|---------|-----|--------|-------|
| **UI (Frontend)** | https://dev.ui.diocesanvitality.org | 🔧 Pending | Service deployed, container images needed |
| **API (Backend)** | https://dev.api.diocesanvitality.org | 🔧 Pending | Service deployed, container images needed |
| **ArgoCD** | https://dev.argocd.diocesanvitality.org | 🔧 SSL Issue | DNS resolves, tunnel/SSL troubleshooting needed |

### **Staging Environment**
| Service | URL | Status | Notes |
|---------|-----|--------|-------|
| **UI (Frontend)** | https://stg.ui.diocesanvitality.org | 🔧 Pending | Service deployment in progress |
| **API (Backend)** | https://stg.api.diocesanvitality.org | 🔧 Pending | Service deployment in progress |
| **ArgoCD** | https://stg.argocd.diocesanvitality.org | 🔧 SSL Issue | DNS resolves, tunnel/SSL troubleshooting needed |

### **Production Environment**
| Service | URL | Status | Notes |
|---------|-----|--------|-------|
| **UI (Frontend)** | https://ui.diocesanvitality.org | 🚧 Not deployed | Infrastructure pending |
| **API (Backend)** | https://api.diocesanvitality.org | 🚧 Not deployed | Infrastructure pending |
| **ArgoCD** | https://argocd.diocesanvitality.org | 🚧 Not deployed | Infrastructure pending |

## 🏗️ Infrastructure Status

### **Development (dev)**
- **Cluster**: `dv-dev` ✅ Running
- **Tunnel**: `e3022377-6206-48b5-8347-81bad3f6434b` ✅ Active (4 connections)
- **ArgoCD**: ✅ Installed and managing applications
- **Applications**: 🔧 Services deployed, awaiting container images

### **Staging (stg)**
- **Cluster**: `dv-stg` ✅ Running
- **Tunnel**: `59509582-7efd-41e9-8080-98a3814aa1bd` ✅ Active (4 connections)
- **ArgoCD**: ✅ Installed and managing applications
- **Applications**: 🔧 Deployment in progress

### **Production (prod)**
- **Cluster**: 🚧 Not created
- **Tunnel**: 🚧 Not created
- **ArgoCD**: 🚧 Not deployed
- **Applications**: 🚧 Not deployed

## 🔐 Access Information

### **ArgoCD Login**
- **Username**: `admin`
- **Password**: Stored in `.argocd-admin-password` file (environment-specific)
- **Dev Cluster Context**: `do-nyc2-dv-dev`
- **Staging Cluster Context**: `do-nyc2-dv-stg`

### **Kubernetes Access**
```bash
# Switch to development
kubectl config use-context do-nyc2-dv-dev

# Switch to staging
kubectl config use-context do-nyc2-dv-stg
```

## 📋 Quick Infrastructure Commands

### **Create Full Environment**
```bash
# Development
make infra-setup CLUSTER_LABEL=dev

# Staging
make infra-setup CLUSTER_LABEL=stg

# Production (when ready)
make infra-setup CLUSTER_LABEL=prd
```

### **Check Status**
```bash
# View all applications
kubectl get applications -n argocd

# Check service status
kubectl get services -n diocesan-vitality-{env}

# View tunnel status
kubectl get pods -n cloudflare-tunnel-{env}
```

## 🔄 GitOps Workflow

- **Infrastructure**: Managed from `main` branch
- **Applications**: Deployed from `develop` branch (dev/staging)
- **Repository**: https://github.com/tomknightatl/diocesan-vitality
- **Manifests**: `k8s/environments/{environment}/`

## 📅 Last Updated

**Date**: September 21, 2025
**Infrastructure Status**: Development and Staging operational, Production pending
**GitOps Status**: Fully automated deployment pipeline active
