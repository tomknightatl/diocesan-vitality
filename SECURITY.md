# Security Policy

## Supported Versions

We actively maintain and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| main    | ✅ Yes             |
| develop | ✅ Yes (latest)    |
| < 1.0   | ❌ No              |

## Reporting a Vulnerability

We take the security of the Diocesan Vitality project seriously. If you discover a security vulnerability, please report it responsibly.

### 🚨 For Security Issues

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please report security issues privately:

1. **Email**: Send details to `security@diocesanvitality.org` (if available)
2. **GitHub Security Advisory**: Use GitHub's private vulnerability reporting feature
3. **Encrypted Communication**: For sensitive issues, request our PGP key

### 📋 What to Include

When reporting a security vulnerability, please include:

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Potential impact** and severity assessment
- **Suggested fix** (if you have one)
- **Your contact information** for follow-up questions

### ⏱️ Response Timeline

- **Initial Response**: Within 48 hours
- **Triage**: Within 1 week
- **Fix Development**: Timeline depends on severity
- **Public Disclosure**: After fix is deployed (coordinated disclosure)

## Security Considerations

### 🔐 Data Protection

#### Sensitive Information
- **API Keys**: Never commit API keys, tokens, or credentials to the repository
- **Database Credentials**: Store securely in environment variables
- **Personal Data**: Minimize collection of personal information
- **Encrypted Storage**: Sensitive data should be encrypted at rest

#### Data Collection Ethics
- **Public Data Only**: Only collect publicly available information
- **Respectful Scraping**: Honor robots.txt and rate limits
- **Data Retention**: Implement appropriate data retention policies
- **Access Controls**: Limit data access to authorized personnel only

### 🌐 Web Scraping Security

#### Respectful Automation
```python
# Example: Respectful rate limiting
import time
import requests

def respectful_request(url, delay=2.5):
    """Make a request with appropriate delay"""
    time.sleep(delay)  # Minimum 2 second delay
    response = requests.get(url, timeout=30)
    return response
```

#### Circuit Breaker Protection
- **Automatic Stopping**: Stop requests when sites return errors
- **Rate Limit Detection**: Detect and respect 429 Too Many Requests
- **Robots.txt Compliance**: Check and honor robots.txt files
- **User-Agent Identification**: Use clear, identifiable User-Agent strings

### 🛡️ Infrastructure Security

#### Container Security
- **Base Images**: Use official, security-updated base images
- **Vulnerability Scanning**: Regularly scan container images
- **Minimal Privileges**: Run containers with minimal required privileges
- **Secrets Management**: Use Kubernetes secrets or similar for sensitive data

#### Kubernetes Security
```yaml
# Example: Security context
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
```

#### Network Security
- **TLS Encryption**: Use HTTPS/TLS for all communications
- **Network Policies**: Implement Kubernetes network policies
- **Firewall Rules**: Restrict unnecessary network access
- **VPN Access**: Use VPN for administrative access when possible

### 🔍 Code Security

#### Input Validation
```python
# Example: Validate diocese ID input
def validate_diocese_id(diocese_id: str) -> int:
    """Validate and sanitize diocese ID input"""
    try:
        id_int = int(diocese_id)
        if id_int < 1 or id_int > 9999:
            raise ValueError("Diocese ID must be between 1 and 9999")
        return id_int
    except ValueError as e:
        raise ValueError(f"Invalid diocese ID: {e}")
```

#### SQL Injection Prevention
```python
# Example: Use parameterized queries
def get_parish_by_id(parish_id: int):
    """Safely query parish by ID"""
    query = "SELECT * FROM parishes WHERE id = %s"
    # Use parameterized query, not string formatting
    result = db.execute(query, (parish_id,))
    return result
```

#### Environment Variables
```bash
# Example: Secure environment variable handling
# In .env (never commit this file)
SUPABASE_KEY=your_secure_key_here
GENAI_API_KEY=your_api_key_here

# In code - validate environment variables
import os
def get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Required environment variable {var_name} not set")
    return value
```

### 🧪 Security Testing

#### Automated Security Scanning
- **Dependency Scanning**: Regular security audits of dependencies
- **Code Analysis**: Static code analysis for security issues
- **Container Scanning**: Vulnerability scanning of Docker images
- **Secret Detection**: Automated detection of committed secrets

#### Manual Security Reviews
- **Code Reviews**: Security-focused code review process
- **Penetration Testing**: Periodic security assessments
- **Access Reviews**: Regular review of access permissions
- **Incident Response**: Documented response procedures

## 🔧 Security Best Practices

### For Contributors

#### Development Environment
```bash
# Use virtual environments
python3 -m venv .venv
source .venv/bin/activate

# Keep dependencies updated
pip install --upgrade pip
pip install -r requirements.txt

# Scan for vulnerabilities
pip-audit
safety check
```

#### Code Practices
- **No Hardcoded Secrets**: Use environment variables or secure vaults
- **Input Sanitization**: Validate all user inputs
- **Error Handling**: Don't expose sensitive information in error messages
- **Logging**: Be careful not to log sensitive data

#### Git Practices
```bash
# Before committing, check for secrets
git diff --cached | grep -E "(api_key|password|token|secret)"

# Use git hooks to prevent secret commits
# See .pre-commit-config.yaml for automated checks
```

### For Deployments

#### Production Security
- **Environment Separation**: Separate dev/staging/production environments
- **Access Controls**: Implement principle of least privilege
- **Monitoring**: Set up security monitoring and alerting
- **Backup Security**: Secure and encrypt backup data

#### API Security
```python
# Example: Rate limiting
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["100 per hour"]
)

@app.route("/api/dioceses")
@limiter.limit("10 per minute")
def get_dioceses():
    # API implementation
    pass
```

## 🚀 Deployment Security

### Docker Security
```dockerfile
# Example: Secure Dockerfile practices
FROM python:3.12-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash diocesan
USER diocesan

# Set secure permissions
COPY --chown=diocesan:diocesan . /app
WORKDIR /app

# Don't run as root
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Security
```yaml
# Example: Secure deployment configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deployment
spec:
  template:
    spec:
      serviceAccountName: diocesan-vitality-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: backend
        image: tomatl/diocesan-vitality:backend-latest
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"
```

## 📞 Contact Information

### Security Team
- **Primary Contact**: Create a GitHub issue with "security" label for non-sensitive issues
- **Private Vulnerabilities**: Use GitHub's private vulnerability reporting
- **General Questions**: See [CONTRIBUTING.md](CONTRIBUTING.md) for community guidelines

### Response Team
Our security response team includes:
- Project maintainers
- DevOps/Infrastructure specialists
- Security advisors (as needed)

## 📚 Additional Resources

### Security Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Kubernetes Security Guide](https://kubernetes.io/docs/concepts/security/)
- [Python Security Guidelines](https://python-security.readthedocs.io/)

### Tools and References
- [Bandit](https://bandit.readthedocs.io/) - Python security linter
- [Safety](https://github.com/pyupio/safety) - Dependency vulnerability scanner
- [Trivy](https://trivy.dev/) - Container vulnerability scanner
- [SAST Tools](https://owasp.org/www-community/Source_Code_Analysis_Tools)

---

**Remember**: Security is everyone's responsibility. When in doubt, ask questions and err on the side of caution.

**Thank you** for helping keep the Diocesan Vitality project and our community safe! 🛡️