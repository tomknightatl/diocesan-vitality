# Documentation Index

**Complete index of all documentation for the Diocesan Vitality project.**

## Table of Contents

- [Getting Started](#getting-started)
- [Database Management](#database-management)
- [Deployment & Operations](#deployment--operations)
- [System Architecture](#system-architecture)
- [Application Components](#application-components)
- [Performance & Optimization](#performance--optimization)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Advanced Features](#advanced-features)
- [Project Configuration](#project-configuration)
- [External Resources](#external-resources)

---

## Getting Started

### 📋 Main Documentation

- **[README.md](../README.md)**: Main project documentation and overview
- **[docs/LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)**: Complete local development setup and workflow
- **[docs/DEVELOPMENT_ENVIRONMENTS.md](DEVELOPMENT_ENVIRONMENTS.md)**: Development environment setup (local and cloud)
- **[docs/COMMANDS.md](COMMANDS.md)**: Complete command reference for all scripts

### 🚀 Quick Start

1. **Prerequisites**: Python 3.12+, Node.js 20+, Chrome browser
2. **Environment Setup**: Clone repository, create virtual environment, install dependencies
3. **Configuration**: Set up `.env` file with API keys
4. **Development**: Start backend, frontend, and pipeline services

**→ Follow [Local Development Guide](LOCAL_DEVELOPMENT.md) for detailed step-by-step instructions.**

---

## Database Management

### 📚 Core Database Documentation

- **[docs/DATABASE_QUICK_REFERENCE.md](DATABASE_QUICK_REFERENCE.md)**: Complete quick reference for database operations, migrations, and management
- **[docs/SCHEMA_CHANGE_MANAGEMENT.md](SCHEMA_CHANGE_MANAGEMENT.md)**: Comprehensive guide for managing database schema changes
- **[docs/SCHEMA_CHANGE_QUICK_REFERENCE.md](SCHEMA_CHANGE_QUICK_REFERENCE.md)**: Quick reference for schema change workflows
- **[docs/PRODUCTION_MIGRATION_GUIDE.md](PRODUCTION_MIGRATION_GUIDE.md)**: Production deployment guide for database migrations

### 🔧 Supabase CLI Documentation

- **[docs/supabase-migration-reference.md](supabase-migration-reference.md)**: Comprehensive Supabase CLI reference for database operations
- **[docs/supabase-migration-quick-reference.md](supabase-migration-quick-reference.md)**: Supabase CLI cheat sheet for common database operations

### 🧪 Database Testing

- **[docs/END_TO_END_TEST_REPORT.md](END_TO_END_TEST_REPORT.md)**: Comprehensive end-to-end testing report for database operations
- **[docs/E2E_TESTING_SUMMARY.md](E2E_TESTING_SUMMARY.md)**: Testing summary and results overview
- **[docs/ACTIONABLE_RECOMMENDATIONS.md](ACTIONABLE_RECOMMENDATIONS.md)**: Implementation recommendations based on testing results
- **[docs/TESTING_COMPLETION_SUMMARY.md](TESTING_COMPLETION_SUMMARY.md)**: Testing completion summary and final status

### 🗄️ Database Scripts

- **[scripts/reset_local_database.py](../scripts/reset_local_database.py)**: Database reset workflow with production data sync
- **[scripts/apply_schema_change.py](../scripts/apply_schema_change.py)**: Schema change management with automatic migration generation
- **[scripts/test_migration.py](../scripts/test_migration.py)**: Migration testing and validation framework
- **[scripts/deploy_to_production.py](../scripts/deploy_to_production.py)**: Production deployment with safety checks
- **[scripts/backup_production_database.py](../scripts/backup_production_database.py)**: Database backup and restore utilities

### 📊 Database Schema

- **[sql/initial_schema.sql](../sql/initial_schema.sql)**: Initial database schema definition
- **[docs/DATABASE.md](DATABASE.md)**: Database schema and data management documentation
- **[sql/migrations/README.md](../sql/migrations/README.md)**: Database migration procedures

---

## Deployment & Operations

### 🚀 Deployment Guides

- **[docs/DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**: Docker and Kubernetes deployment instructions
- **[docs/CI_CD_PIPELINE.md](CI_CD_PIPELINE.md)**: Complete CI/CD pipeline documentation and workflows
- **[docs/GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)**: GitHub Actions setup and configuration

### 🏗️ Infrastructure Management

- **[docs/TERRAFORM_INFRASTRUCTURE.md](TERRAFORM_INFRASTRUCTURE.md)**: Terraform infrastructure management (hybrid Terraform + GitOps approach)
- **[k8s/README.md](../k8s/README.md)**: Kubernetes deployment and pipeline management
- **[k8s/SCALING_README.md](../k8s/SCALING_README.md)**: Horizontal scaling documentation
- **[k8s/cluster-management/README.md](../k8s/cluster-management/README.md)**: Cluster management scripts and infrastructure setup

### 🔧 GitOps & Configuration

- **[k8s/argocd/README.md](../k8s/argocd/README.md)**: ArgoCD GitOps configuration
- **[k8s/argocd/bitnami-sealed-secrets-application-set-README.md](../k8s/argocd/bitnami-sealed-secrets-application-set-README.md)**: Sealed secrets management
- **[k8s/argocd/cloudflare-tunnel-applicationsetREADME.md](../k8s/argocd/cloudflare-tunnel-applicationsetREADME.md)**: Cloudflare tunnel configuration

### 🌐 Cloud Services

- **[docs/CLOUDFLARE.md](CLOUDFLARE.md)**: Cloudflare tunnel and DNS configuration
- **[docs/supabase-setup.md](supabase-setup.md)**: Database setup instructions

---

## System Architecture

### 🏗️ Architecture Documentation

- **[docs/ARCHITECTURE.md](ARCHITECTURE.md)**: System architecture and design patterns
- **[docs/MONITORING.md](MONITORING.md)**: Real-time monitoring and operational visibility

### 🔐 Security & Authentication

- **[docs/AUTHENTICATION.md](AUTHENTICATION.md)**: Authentication and security configuration

### 🌐 Network & Infrastructure

- **[docs/CLOUDFLARE.md](CLOUDFLARE.md)**: Cloudflare tunnel and DNS configuration
- **[docs/TERRAFORM_INFRASTRUCTURE.md](TERRAFORM_INFRASTRUCTURE.md)**: Infrastructure as code with Terraform

---

## Application Components

### 🖥️ Backend & Frontend

- **[backend/README.md](../backend/README.md)**: FastAPI backend server documentation
- **[frontend/README.md](../frontend/README.md)**: React frontend application setup

### 🔄 Pipeline & Data Processing

- **[pipeline/run_pipeline.py](../pipeline/run_pipeline.py)**: Main orchestration script for the entire extraction pipeline
- **[pipeline/async_extract_parishes.py](../pipeline/async_extract_parishes.py)**: High-performance concurrent extraction (60% faster)
- **[pipeline/distributed_pipeline_runner.py](../pipeline/distributed_pipeline_runner.py)**: Distributed pipeline for Kubernetes deployment

### 🧩 Core Components

- **[core/](../core/)**: Essential utilities for database, WebDriver, and circuit breaker management
- **[parish_extractors.py](../parish_extractors.py)**: Multi-platform parish extraction system
- **[llm_utils.py](../llm_utils.py)**: AI-powered content analysis with Google Gemini

---

## Performance & Optimization

### ⚡ Performance Guides

- **[docs/ASYNC_PERFORMANCE_GUIDE.md](ASYNC_PERFORMANCE_GUIDE.md)**: High-performance concurrent extraction optimization
- **[docs/ml-model-training.md](ml-model-training.md)**: ML-based URL prediction system training

### 🤖 Machine Learning

- **[docs/ml-model-training.md](ml-model-training.md)**: ML-based URL prediction system training and optimization
- **[pipeline/ml_url_predictor.py](../pipeline/ml_url_predictor.py)**: ML-based URL prediction implementation

### 📊 Monitoring & Analytics

- **[docs/MONITORING.md](MONITORING.md)**: Real-time monitoring and operational visibility
- **[report_statistics.py](../report_statistics.py)**: Statistics and visualization script for collected data

---

## Testing & Quality Assurance

### 🧪 Testing Framework

- **[tests/TESTING.md](../tests/TESTING.md)**: Testing framework and test procedures

### 🗄️ Database Testing

- **[docs/END_TO_END_TEST_REPORT.md](END_TO_END_TEST_REPORT.md)**: Comprehensive end-to-end testing report for database operations
- **[docs/E2E_TESTING_SUMMARY.md](E2E_TESTING_SUMMARY.md)**: Testing summary and results overview
- **[docs/ACTIONABLE_RECOMMENDATIONS.md](ACTIONABLE_RECOMMENDATIONS.md)**: Implementation recommendations based on testing results
- **[docs/TESTING_COMPLETION_SUMMARY.md](TESTING_COMPLETION_SUMMARY.md)**: Testing completion summary and final status

### 🔍 Quality Assurance

- **[scripts/test_migration.py](../scripts/test_migration.py)**: Migration testing and validation framework
- **[tests/](../tests/)**: Complete test suite for all components

---

## Advanced Features

### 🎯 Specialized Features

- **[docs/DIOCESE_PARISH_DIRECTORY_OVERRIDE.md](DIOCESE_PARISH_DIRECTORY_OVERRIDE.md)**: Directory URL override system
- **[pipeline/async_extract_parishes.py](../pipeline/async_extract_parishes.py)**: High-performance concurrent extraction

### 🤖 AI Integration

- **[llm_utils.py](../llm_utils.py)**: AI-powered content analysis with Google Gemini
- **[pipeline/ml_url_predictor.py](../pipeline/ml_url_predictor.py)**: ML-based URL prediction system

### 🔄 Distributed Systems

- **[pipeline/distributed_pipeline_runner.py](../pipeline/distributed_pipeline_runner.py)**: Distributed pipeline for Kubernetes deployment
- **[k8s/SCALING_README.md](../k8s/SCALING_README.md)**: Horizontal scaling documentation

---

## Project Configuration

### ⚙️ Configuration Files

- **[.claude/CLAUDE.md](../.claude/CLAUDE.md)**: Claude Code assistant project instructions and commands
- **[Makefile](../Makefile)**: Build and deployment commands
- **[.env.example](../.env.example)**: Environment configuration template

### 📝 Project Structure

- **[README.md](../README.md)**: Main project documentation and structure overview
- **[docs/ARCHITECTURE.md](ARCHITECTURE.md)**: System architecture and component specifications

---

## External Resources

### 🌐 Official Documentation

- **[Supabase Documentation](https://supabase.com/docs)**: Official Supabase platform documentation
- **[Supabase CLI Reference](https://supabase.com/docs/guides/cli)**: Supabase CLI command reference
- **[PostgreSQL Documentation](https://www.postgresql.org/docs/)**: PostgreSQL database documentation
- **[FastAPI Documentation](https://fastapi.tiangolo.com/)**: FastAPI framework documentation
- **[React Documentation](https://react.dev/)**: React framework documentation
- **[Kubernetes Documentation](https://kubernetes.io/docs/)**: Kubernetes orchestration documentation

### 🛠️ Tools & Libraries

- **[Selenium Documentation](https://www.selenium.dev/documentation/)**: Web automation framework
- **[Google Gemini API](https://ai.google.dev/gemini-api)**: AI-powered content analysis
- **[Docker Documentation](https://docs.docker.com/)**: Container platform documentation
- **[GitHub Actions Documentation](https://docs.github.com/en/actions)**: CI/CD automation documentation

### 📚 Learning Resources

- **[Python Documentation](https://docs.python.org/3/)**: Python programming language
- **[TypeScript Documentation](https://www.typescriptlang.org/docs/)**: TypeScript language documentation
- **[Node.js Documentation](https://nodejs.org/docs/)**: Node.js runtime documentation

---

## Documentation by Category

### 🚀 For New Users

1. **[README.md](../README.md)** - Start here for project overview
2. **[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)** - Set up your development environment
3. **[DATABASE_QUICK_REFERENCE.md](DATABASE_QUICK_REFERENCE.md)** - Learn database operations
4. **[COMMANDS.md](COMMANDS.md)** - Understand available commands

### 🔧 For Developers

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Understand system design
2. **[DEVELOPMENT_ENVIRONMENTS.md](DEVELOPMENT_ENVIRONMENTS.md)** - Set up development environments
3. **[SCHEMA_CHANGE_MANAGEMENT.md](SCHEMA_CHANGE_MANAGEMENT.md)** - Manage database changes
4. **[ASYNC_PERFORMANCE_GUIDE.md](ASYNC_PERFORMANCE_GUIDE.md)** - Optimize performance

### 🚀 For DevOps Engineers

1. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Deploy the system
2. **[CI_CD_PIPELINE.md](CI_CD_PIPELINE.md)** - Understand CI/CD workflow
3. **[TERRAFORM_INFRASTRUCTURE.md](TERRAFORM_INFRASTRUCTURE.md)** - Manage infrastructure
4. **[k8s/README.md](../k8s/README.md)** - Kubernetes deployment

### 🗄️ For Database Administrators

1. **[DATABASE_QUICK_REFERENCE.md](DATABASE_QUICK_REFERENCE.md)** - Quick command reference
2. **[SCHEMA_CHANGE_MANAGEMENT.md](SCHEMA_CHANGE_MANAGEMENT.md)** - Schema change workflows
3. **[PRODUCTION_MIGRATION_GUIDE.md](PRODUCTION_MIGRATION_GUIDE.md)** - Production deployments
4. **[END_TO_END_TEST_REPORT.md](END_TO_END_TEST_REPORT.md)** - Testing validation

### 🧪 For QA Engineers

1. **[tests/TESTING.md](../tests/TESTING.md)** - Testing framework overview
2. **[END_TO_END_TEST_REPORT.md](END_TO_END_TEST_REPORT.md)** - Testing results
3. **[ACTIONABLE_RECOMMENDATIONS.md](ACTIONABLE_RECOMMENDATIONS.md)** - Quality improvements
4. **[scripts/test_migration.py](../scripts/test_migration.py)** - Migration testing

---

## Quick Reference

### 🚀 Common Workflows

#### Local Development Setup
```bash
# 1. Clone and setup
git clone <repository>
cd diocesan-vitality
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start services
make start
```

#### Database Schema Change
```bash
# 1. Make schema changes locally
supabase db query --local "ALTER TABLE users ADD COLUMN last_login TIMESTAMPTZ;"

# 2. Generate and apply migration
python scripts/apply_schema_change.py --auto --name "add_users_last_login"

# 3. Test migration
python scripts/test_migration.py

# 4. Deploy to production
python scripts/deploy_to_production.py --auto --migration-file "migration.sql"
```

#### Production Deployment
```bash
# 1. Validate migration
python scripts/deploy_to_production.py --validate --migration-file "migration.sql"

# 2. Create backup
python scripts/deploy_to_production.py --backup-only

# 3. Deploy to production
python scripts/deploy_to_production.py --auto --migration-file "migration.sql"

# 4. Monitor deployment
tail -f logs/production_deployment_*.log
```

### 📋 Essential Commands

```bash
# Database operations
make db-check                    # Test database connection
python scripts/reset_local_database.py  # Reset local database
python scripts/apply_schema_change.py --auto --name "change"  # Apply schema change

# Development operations
make start                      # Start development services
make stop                       # Stop development services
make test                       # Run tests

# Production operations
python scripts/deploy_to_production.py --auto --migration-file "migration.sql"  # Deploy
python scripts/backup_production_database.py  # Create backup
```

---

## Documentation Standards

### 📝 Documentation Guidelines

All documentation in this project follows these standards:

- **Comprehensive**: Complete coverage of topics with examples
- **Accurate**: Technical content verified and tested
- **Current**: Regular updates to reflect system changes
- **Accessible**: Clear language and logical organization
- **Maintainable**: Easy to update and extend

### 🔄 Documentation Maintenance

Documentation is maintained through:

- **Regular Reviews**: Periodic review for accuracy and completeness
- **Version Control**: All documentation tracked in Git
- **Change Logs**: Documentation updates logged with system changes
- **Feedback Integration**: User feedback incorporated into improvements

### 📊 Documentation Quality

Quality assurance for documentation includes:

- **Technical Verification**: All commands and procedures tested
- **Cross-References**: Consistent linking between related documents
- **Style Consistency**: Uniform formatting and structure
- **Accessibility**: Clear navigation and searchability

---

## Support and Resources

### 🆘 Getting Help

1. **Documentation**: Check relevant documentation files first
2. **Logs**: Review log files in `logs/` directory
3. **Test Results**: Check `test_reports/` for detailed output
4. **Environment**: Verify `.env` configuration
5. **Community**: Check project issues and discussions

### 📞 Contact & Support

- **Documentation Issues**: Report via GitHub issues
- **Technical Questions**: Use project discussions
- **Feature Requests**: Submit via GitHub issues
- **Bug Reports**: Include logs and environment details

### 🔍 Troubleshooting

For common issues and solutions:

1. **Database Issues**: Check [DATABASE_QUICK_REFERENCE.md](DATABASE_QUICK_REFERENCE.md)
2. **Deployment Issues**: Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. **Performance Issues**: Check [ASYNC_PERFORMANCE_GUIDE.md](ASYNC_PERFORMANCE_GUIDE.md)
4. **Testing Issues**: Check [tests/TESTING.md](../tests/TESTING.md)

---

## Summary

This documentation index provides comprehensive access to all project documentation organized by category and use case. Key points:

- **Getting Started**: Begin with README.md and LOCAL_DEVELOPMENT.md
- **Database Management**: Use DATABASE_QUICK_REFERENCE.md for daily operations
- **Deployment**: Follow DEPLOYMENT_GUIDE.md for production deployments
- **Development**: Refer to ARCHITECTURE.md and COMMANDS.md for development work
- **Testing**: Check END_TO_END_TEST_REPORT.md for testing validation
- **Support**: Use relevant documentation and community resources for assistance

For specific questions or issues, refer to the appropriate documentation section or contact the project team through GitHub issues and discussions.

---

*Last Updated: June 21, 2026*  
*Version: 1.0*  
*Project: Diocesan Vitality*