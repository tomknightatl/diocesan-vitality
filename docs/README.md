# Documentation Index

This directory contains comprehensive documentation for the Diocesan Vitality project.

## 📖 Getting Started

| Document | Description |
|----------|-------------|
| [Local Development](LOCAL_DEVELOPMENT.md) | Complete setup guide for local development |
| [Commands Reference](COMMANDS.md) | All available commands and usage |
| [Release Automation](RELEASE_AUTOMATION_GUIDE.md) | How to use semantic release system |

## 🏗️ Architecture & Design

| Document | Description |
|----------|-------------|
| [System Architecture](ARCHITECTURE.md) | Overall system design and components |
| [Database Schema](DATABASE.md) | Database structure and operations |
| [Authentication](AUTHENTICATION.md) | Security and authentication setup |

## 🚀 Deployment & Operations

| Document | Description |
|----------|-------------|
| [Deployment Guide](DEPLOYMENT_GUIDE.md) | Docker and Kubernetes deployment |
| [CI/CD Pipeline](CI_CD_PIPELINE.md) | Continuous integration and deployment |
| [Infrastructure Setup](INFRASTRUCTURE_SETUP.md) | Cloud infrastructure configuration |
| [Development Environments](DEVELOPMENT_ENVIRONMENTS.md) | Environment management |

## 🔧 Advanced Topics

| Document | Description |
|----------|-------------|
| [Performance Guide](ASYNC_PERFORMANCE_GUIDE.md) | Async processing and optimization |
| [Monitoring](MONITORING.md) | System monitoring and alerting |
| [ML Model Training](ml-model-training.md) | Machine learning URL prediction |

## ☁️ Infrastructure

| Document | Description |
|----------|-------------|
| [Terraform Infrastructure](TERRAFORM_INFRASTRUCTURE.md) | Infrastructure as code |
| [Infrastructure Commands](INFRASTRUCTURE_COMMANDS.md) | Infrastructure management |
| [Cloudflare Setup](CLOUDFLARE.md) | CDN and security configuration |
| [Environment URLs](ENVIRONMENT_URLS.md) | Service endpoints and URLs |

## 🔀 Specialized Documentation

| Document | Description |
|----------|-------------|
| [Diocese Directory Override](DIOCESE_PARISH_DIRECTORY_OVERRIDE.md) | Custom directory configuration |
| [GitHub Actions Setup](GITHUB_ACTIONS_SETUP.md) | CI/CD configuration |
| [Supabase Setup](supabase-setup.md) | Database configuration |

## 📁 Component Documentation

Additional documentation is available in component-specific directories:

- **[Backend Documentation](../backend/README.md)** - FastAPI backend service
- **[Frontend Documentation](../frontend/README.md)** - React dashboard
- **[Kubernetes Documentation](../k8s/README.md)** - Deployment manifests
- **[Testing Documentation](../tests/TESTING.md)** - Test suite and procedures
- **[Terraform Documentation](../terraform/README.md)** - Infrastructure code

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/tomknightatl/diocesan-vitality/issues)
- **Contributing**: [Contributing Guide](../CONTRIBUTING.md)
- **Security**: [Security Policy](../SECURITY.md)
- **Code of Conduct**: [Code of Conduct](../CODE_OF_CONDUCT.md)

## 📝 Quick Reference

### Development Commands
```bash
make install    # Setup development environment
make start      # Start backend only
make start-full # Start backend + frontend
make test-quick # Run quick tests
make lint       # Code linting
make format     # Code formatting
```

### Release Commands
```bash
# Feature release
git commit -m "feat: add new feature"

# Bug fix release
git commit -m "fix: resolve issue"

# Breaking change release
git commit -m "feat!: breaking change"
```

### Infrastructure Commands
```bash
# Deploy to development
make cluster-dev-deploy

# Check cluster status
kubectl get pods -n diocesan-vitality-dev

# View logs
kubectl logs deployment/backend-deployment -n diocesan-vitality-dev
```

---

For questions about any documentation, please create an issue or refer to the [Contributing Guide](../CONTRIBUTING.md).