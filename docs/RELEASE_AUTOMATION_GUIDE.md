# Release Automation Guide

This guide explains how to use the new semantic release automation system implemented in the Diocesan Vitality project.

## Overview

The project now uses **semantic versioning** with **conventional commits** to automatically manage releases, build Docker images, and deploy to production. This replaces the previous timestamp-based versioning system.

## Quick Start

### 1. Making a Release

Instead of manually tagging versions, simply use conventional commit messages:

```bash
# For a patch release (bug fixes)
git commit -m "fix: resolve parish data extraction timeout"

# For a minor release (new features)
git commit -m "feat: add mass schedule filtering by language"

# For a major release (breaking changes)
git commit -m "feat!: redesign API endpoints

BREAKING CHANGE: All API endpoints now require authentication"
```

### 2. Triggering the Release

Push to the main branch:

```bash
git push origin main
```

The system will automatically:
- Determine the version bump based on commit messages
- Generate a changelog
- Build multi-architecture Docker images
- Update Kubernetes manifests
- Create a GitHub release

## Conventional Commit Format

### Basic Structure
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Version Bump | Description | Example |
|------|--------------|-------------|---------|
| `fix:` | **Patch** (0.0.X) | Bug fixes | `fix: handle null parish addresses` |
| `feat:` | **Minor** (0.X.0) | New features | `feat: add diocese contact information` |
| `feat!:` or `BREAKING CHANGE:` | **Major** (X.0.0) | Breaking changes | `feat!: require API authentication` |
| `docs:` | No release | Documentation only | `docs: update API examples` |
| `style:` | No release | Code formatting | `style: fix indentation in parser` |
| `refactor:` | No release | Code refactoring | `refactor: extract validation logic` |
| `test:` | No release | Adding tests | `test: add parish extraction tests` |
| `chore:` | No release | Maintenance tasks | `chore: update dependencies` |

### Examples

#### Patch Release (Bug Fix)
```bash
git commit -m "fix: handle missing mass schedule data gracefully

Previously the extractor would crash when parishes had no mass
schedule information. Now it logs a warning and continues."
```

#### Minor Release (New Feature)
```bash
git commit -m "feat: add support for Spanish-language parish websites

- Detect Spanish content automatically
- Extract masa schedules in Spanish format
- Add language field to parish data model"
```

#### Major Release (Breaking Change)
```bash
git commit -m "feat!: restructure parish data schema

BREAKING CHANGE: The parish data structure has changed.
- Renamed 'contact_info' to 'contacts'
- Split address into separate fields
- Moved mass_schedules to separate table

Migration guide: see docs/MIGRATION.md"
```

## Release Workflow

### Automatic Process

1. **Commit Analysis**: System analyzes commit messages since last release
2. **Version Calculation**: Determines new version based on conventional commits
3. **Changelog Generation**: Creates changelog from commit messages
4. **Version Updates**: Updates all version references in code
5. **Docker Builds**: Builds multi-architecture images with semantic tags
6. **Manifest Updates**: Updates Kubernetes deployment manifests
7. **GitHub Release**: Creates GitHub release with generated notes

### Manual Trigger (Dry Run)

To test what would be released without actually releasing:

```bash
# Go to GitHub Actions
# Run "Automated Release" workflow
# Set "dry_run" to true
```

## Docker Image Tagging

### New Semantic Tags
```
tomatl/diocesan-vitality:backend-1.2.3
tomatl/diocesan-vitality:frontend-1.2.3
tomatl/diocesan-vitality:pipeline-1.2.3
```

### Additional Tags
```
tomatl/diocesan-vitality:backend-1        # Major version
tomatl/diocesan-vitality:backend-latest   # Latest release
```

## Kubernetes Deployment

### GitOps Workflow

1. **Automatic Updates**: Release workflow updates manifest files in `k8s/` directory
2. **ArgoCD Sync**: ArgoCD detects changes and syncs to cluster
3. **Deployment**: New images are deployed automatically

### Manual Deployment Verification

```bash
# Check current versions in cluster
kubectl get deployments -o jsonpath='{.items[*].spec.template.spec.containers[*].image}' | tr ' ' '\n'

# Watch deployment progress
kubectl rollout status deployment/backend-deployment
kubectl rollout status deployment/frontend-deployment
kubectl rollout status deployment/pipeline-deployment
```

## Version Management

### Current Version Check

```bash
# Python package version
python -c "from diocesan_vitality import __version__; print(__version__)"

# Docker image versions
docker images tomatl/diocesan-vitality --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}"
```

### Version File Structure

The version is centrally managed in `src/diocesan_vitality/__version__.py`:

```python
__version__ = "1.2.3"
__version_info__ = (1, 2, 3)

BUILD_INFO = {
    "version": "1.2.3",
    "docker_tags": {
        "backend": "tomatl/diocesan-vitality:backend-1.2.3",
        "frontend": "tomatl/diocesan-vitality:frontend-1.2.3",
        "pipeline": "tomatl/diocesan-vitality:pipeline-1.2.3"
    }
}
```

## Migration from Legacy System

### Legacy vs. New Comparison

| Aspect | Legacy System | New System |
|--------|---------------|------------|
| Versioning | Timestamp-based | Semantic versioning |
| Tags | `backend-2025-09-15-22-58-39` | `backend-1.2.3` |
| Releases | Manual | Automatic |
| Changelogs | Manual | Generated |
| Deployment | Manual manifest updates | GitOps with ArgoCD |

### Skipping Legacy Deployment

To prevent the legacy CI/CD pipeline from deploying, include `[skip-legacy-deploy]` in your commit message:

```bash
git commit -m "feat: add new feature [skip-legacy-deploy]"
```

## Troubleshooting

### Common Issues

#### No Release Generated
**Problem**: Pushed commits but no release was created
**Solution**: Check that commits follow conventional format and contain releasable changes (`feat:`, `fix:`)

#### Version Conflicts
**Problem**: Merge conflicts in version files
**Solution**:
```bash
git pull --rebase
# Resolve conflicts in __version__.py
git add src/diocesan_vitality/__version__.py
git rebase --continue
```

#### Failed Docker Builds
**Problem**: Docker build fails during release
**Solution**: Check that all Dockerfiles accept VERSION, BUILD_DATE, and GIT_COMMIT build args

### Debug Commands

```bash
# Check semantic-release configuration
npx semantic-release --dry-run

# Validate conventional commits
npx commitizen check

# View release workflow logs
gh run list --workflow="Automated Release"
gh run view <run-id>
```

## Best Practices

### Commit Messages
- **Be descriptive**: Explain what and why, not just what
- **Use imperative mood**: "add feature" not "added feature"
- **Reference issues**: Include issue numbers when applicable
- **Group related changes**: Use multi-line commits for complex changes

### Release Strategy
- **Regular releases**: Release frequently with small changes
- **Feature branches**: Use branches for large features, squash merge to main
- **Testing**: Ensure all tests pass before merging to main
- **Documentation**: Update docs as part of feature commits

### Version Planning
- **Patch**: Bug fixes, security updates
- **Minor**: New features, enhancements (backward compatible)
- **Major**: Breaking changes, major refactors

## Advanced Usage

### Custom Release Notes

Add detailed release notes in commit footer:

```bash
git commit -m "feat: add advanced filtering

Add support for filtering parishes by:
- Denomination
- Service language
- Accessibility features

Closes #123, #124"
```

### Multiple Components

When changing multiple components, use scoped commits:

```bash
git commit -m "feat(backend): add new API endpoint"
git commit -m "feat(frontend): add UI for new feature"
git commit -m "docs: update API documentation"
```

### Emergency Releases

For critical bug fixes that need immediate release:

```bash
git commit -m "fix!: critical security vulnerability

SECURITY: Fixes potential data exposure in parish API.
This requires immediate deployment to production."
```

## Monitoring and Observability

### Release Tracking
- **GitHub Releases**: View all releases at https://github.com/tomknightatl/diocesan-vitality/releases
- **Docker Hub**: Monitor image builds at https://hub.docker.com/r/tomatl/diocesan-vitality
- **Deployment Status**: Check ArgoCD dashboard for deployment progress

### Success Metrics
- **Release Frequency**: Track time between releases
- **Deployment Success**: Monitor failed vs. successful deployments
- **Rollback Rate**: Track how often deployments need to be rolled back

## Support

### Getting Help
- **Documentation**: Check `docs/` directory for detailed guides
- **Issues**: Report problems at https://github.com/tomknightatl/diocesan-vitality/issues
- **Discussions**: Use GitHub Discussions for questions

### Contributing
See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed contribution guidelines, including how to use conventional commits effectively.
