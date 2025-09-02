2# Authentication Instructions

This document provides simplified instructions for authenticating with GitHub (gh) and GitHub Container Registry (ghcr.io).

## 1. GitHub Personal Access Token (PAT)

Before proceeding, ensure you have a GitHub Personal Access Token (PAT) with the necessary scopes (e.g., `repo`, `read:packages`, `write:packages`). You can generate one from your GitHub settings:

`Settings` -> `Developer settings` -> `Personal access tokens` -> `Tokens (classic)` -> `Generate new token`

Store this token securely, for example, in an environment variable:

```bash
export GH_TOKEN="YOUR_GITHUB_PAT"
```

## 2. Authenticate with GitHub CLI (gh)

If you have the GitHub CLI installed, you can authenticate by running:

```bash
gh auth login
```

Follow the prompts to authenticate using your web browser or by pasting your PAT.

**Note:** If you have set the `GH_TOKEN` environment variable, `gh auth login` will use it directly and might not go through the interactive credential storage process. If you want `gh` to store credentials for you, unset `GH_TOKEN` before running `gh auth login` (e.g., `unset GH_TOKEN`).

## 3. Authenticate with GitHub Container Registry (ghcr.io)

To authenticate Docker with ghcr.io, use your GitHub username and the PAT as the password:

```bash
echo $GH_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username.