# CI/Pre-commit Workflow Guide

This guide explains how to ensure your code always passes CI by using local tools that exactly match the CI pipeline.

## 🎯 Goal: Zero CI Failures

Our setup ensures that **if your code passes locally, it WILL pass in CI**. No more surprises!

## 🔧 Quick Setup (One-time)

```bash
# 1. Install pre-commit hooks (matches CI exactly)
make pre-commit-install

# 2. Optional: Add to your shell for quick access
echo 'alias ci-check="make ci-check"' >> ~/.bashrc
```

## 🚀 Daily Development Workflow

### Before Every Commit

**Option 1: Automatic (Recommended)**
```bash
git add .
git commit -m "your message"
# Pre-commit hooks run automatically and fix/check your code
```

**Option 2: Manual Check**
```bash
# Run the exact same checks as CI
make ci-check

# If any fail, fix them and re-run
black . && isort .
make ci-check
```

### Core Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `make ci-check` | Run exact CI checks locally | Before committing |
| `make pre-commit-install` | Install/update pre-commit hooks | Setup & updates |
| `black . && isort .` | Auto-fix formatting | When ci-check fails |
| `flake8 .` | Check code quality | Debug specific issues |

## 📋 What Gets Checked

### CI Pipeline Checks (Always Run)
✅ **Black formatting** - Code style consistency
✅ **Import sorting (isort)** - Clean import organization
✅ **Flake8 linting** - Code quality and standards

### Pre-commit Extras (Local Only)
🔍 **Security scan (bandit)** - Find security issues early
🔍 **File quality** - Trailing whitespace, large files, etc.
🔍 **Frontend linting** - ESLint for JS/TS files

## ⚙️ Configuration Files

Our tools read configuration from these files (no command-line overrides):

- **Black**: `pyproject.toml` → line-length=127, Python 3.11+
- **Isort**: `pyproject.toml` → profile=black, line-length=127
- **Flake8**: `.flake8` → max-line-length=127, ignore E203/W503

## 🐛 Troubleshooting

### "Pre-commit hook failed"
```bash
# See what failed
git commit -m "message"

# Fix formatting issues automatically
black . && isort .

# Check what's still broken
make ci-check

# Commit again
git commit -m "message"
```

### "CI failed but local passed"
This should never happen! If it does:

1. Pull latest changes: `git pull origin develop`
2. Update hooks: `make pre-commit-install`
3. Re-run: `make ci-check`
4. If still broken, check [CI workflow](../.github/workflows/simple-ci.yml)

### "Flake8 errors I don't understand"
```bash
# Get detailed explanation
flake8 --statistics --show-source .

# Common fixes:
# E302: Add blank line before function
# F401: Remove unused import
# E501: Line too long (black should fix this)
```

### "Want to skip pre-commit for urgent fix"
```bash
# Skip hooks (NOT RECOMMENDED)
git commit --no-verify -m "urgent fix"

# But immediately fix and re-commit:
make ci-check
git add . && git commit -m "fix: resolve formatting issues"
```

## 🔄 Keeping Everything in Sync

### When CI Workflow Changes
1. Update `.pre-commit-config.yaml` to match
2. Run `make pre-commit-install` to update
3. Test with `make ci-check`

### Monthly Maintenance
```bash
# Update all hook versions
make pre-commit-install

# Verify everything still works
make ci-check
```

## 🎯 Best Practices

### ✅ DO
- Run `make ci-check` before every commit
- Let pre-commit hooks auto-fix issues
- Update hooks monthly
- Use the exact same tool versions as CI

### ❌ DON'T
- Skip pre-commit hooks without good reason
- Add `--no-verify` to your git aliases
- Override tool configurations with command-line args
- Commit without testing locally first

## 🔬 Advanced Usage

### Testing Specific Tools
```bash
# Test individual tools
black --check .
isort --check-only .
flake8 .

# Auto-fix formatting
black .
isort .
```

### Integration with Editors

**VS Code**: Install Python, Black, and Flake8 extensions
```json
{
    "python.formatting.provider": "black",
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true
}
```

**Zed**: Already configured in project settings

### CI Status Monitoring
```bash
# Check current CI status
gh run list --branch develop --limit 3

# View failed CI logs
gh run view --log-failed
```

## 🆘 Getting Help

1. **Check this guide first** - Most issues are covered here
2. **Run `make ci-check`** - See exactly what's failing
3. **Check tool docs**: [Black](https://black.readthedocs.io/), [isort](https://pycqa.github.io/isort/), [Flake8](https://flake8.pycqa.org/)
4. **Ask the team** - Share your `make ci-check` output

## 📈 Success Metrics

You'll know this is working when:
- ✅ CI failures drop to near zero
- ✅ Code reviews focus on logic, not formatting
- ✅ Commits are cleaner and more consistent
- ✅ You can commit with confidence
