# Contributing to Diocesan Vitality

Thank you for your interest in contributing to the Diocesan Vitality project! This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Set up the development environment** following our [Local Development Guide](docs/LOCAL_DEVELOPMENT.md)
4. **Create a feature branch** from `develop`
5. **Make your changes** with tests
6. **Submit a pull request**

## 📋 Ways to Contribute

### 🐛 Bug Reports
- Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml)
- Include system information, steps to reproduce, and expected vs actual behavior
- Check existing issues first to avoid duplicates

### ✨ Feature Requests
- Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml)
- Describe the problem you're trying to solve
- Explain your proposed solution and alternatives considered

### 🔧 Code Contributions
- Parish extractor implementations for new website platforms
- Performance optimizations and bug fixes
- Documentation improvements
- Test coverage enhancements

### 📚 Documentation
- Improve existing documentation
- Add examples and tutorials
- Translate documentation (future)

## 🛠️ Development Setup

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker with buildx support
- Chrome/Chromium browser
- kubectl (for cluster development)

### Environment Setup
```bash
# Clone and setup
git clone https://github.com/tomknightatl/diocesan-vitality.git
cd diocesan-vitality

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install dependencies
make install

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Verify setup
make env-check
make test-quick
```

See the complete [Local Development Guide](docs/LOCAL_DEVELOPMENT.md) for detailed setup instructions.

## 🔄 Development Workflow

### Branch Strategy
- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features and improvements
- `bugfix/*` - Bug fixes
- `hotfix/*` - Critical production fixes

### Making Changes
1. **Create a feature branch:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Follow the existing code style and patterns
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes:**
   ```bash
   # Code quality
   make format
   make lint

   # Run tests
   make test-quick
   pytest tests/ -v

   # Test specific components
   make db-check
   make ai-check
   make webdriver-check
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add new parish extractor for SquareSpace

   - Implement SquareSpace-specific parsing logic
   - Add tests for new extractor
   - Update documentation

   Closes #123"
   ```

### Commit Message Format
We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions or modifications
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `ci:` - CI/CD changes
- `chore:` - Maintenance tasks

**Examples:**
```bash
feat(extractors): add WordPress extractor for parish directories
fix(pipeline): resolve memory leak in async extraction
docs: update cluster development guide
test: add integration tests for AI extractor
```

## 🧪 Testing

### Test Categories
- **Unit tests** - Individual component testing
- **Integration tests** - Component interaction testing
- **End-to-end tests** - Full pipeline testing

### Running Tests
```bash
# All tests
pytest tests/ -v

# Specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=core --cov=extractors --cov-report=html

# Specific test file
pytest tests/test_extractors.py -v
```

### Writing Tests
- Place tests in the `tests/` directory
- Follow existing test patterns and naming conventions
- Mock external dependencies (databases, APIs, web requests)
- Test both success and failure scenarios

## 📝 Code Style

### Python Code Style
We use automated code formatting and linting:

```bash
# Format code
make format
black . --line-length=127

# Check linting
make lint
flake8 . --max-line-length=88 --extend-ignore=E203,W503

# Type checking
mypy . --ignore-missing-imports
```

### Style Guidelines
- **Line length:** 127 characters (Black default)
- **Imports:** Use isort for import organization
- **Docstrings:** Use Google-style docstrings
- **Type hints:** Add type hints for function signatures
- **Error handling:** Use specific exception types
- **Logging:** Use the project's logging system (`core.logger`)

### Frontend Code Style
```bash
cd frontend
npm run lint    # ESLint for JavaScript/React
```

## 🔒 Security Considerations

### Data Handling
- **Never commit API keys or secrets** to the repository
- **Respect robots.txt** and website terms of service
- **Use rate limiting** for web scraping (already implemented)
- **Handle personal data** responsibly (parish contact information)

### Code Security
- **Validate user inputs** in CLI and API endpoints
- **Use secure defaults** for configuration
- **Avoid SQL injection** using parameterized queries
- **Review dependencies** for known vulnerabilities

## 🚀 Deployment

### Local Testing
```bash
# Test pipeline locally
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 5

# Test with monitoring
make pipeline

# Test distributed pipeline
python distributed_pipeline_runner.py --worker_type discovery
```

### Cluster Development
For testing in a Kubernetes environment:
```bash
# Build development images
DEV_TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)-dev
docker buildx build --platform linux/amd64,linux/arm64 \
  -f backend/Dockerfile \
  -t tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP} \
  --push backend/

# Deploy to development cluster
# See docs/LOCAL_DEVELOPMENT.md for complete workflow
```

## 📊 Performance Guidelines

### Web Scraping Ethics
- **Respect rate limits** (2-5 seconds between requests)
- **Honor robots.txt** files
- **Use respectful User-Agent strings**
- **Implement circuit breakers** for failing sites
- **Cache responses** when appropriate

### Code Performance
- **Use async/await** for I/O-bound operations
- **Batch database operations** where possible
- **Monitor memory usage** in long-running processes
- **Profile code** before optimizing

## 🆘 Getting Help

### Documentation
- [Local Development Guide](docs/LOCAL_DEVELOPMENT.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Commands Reference](docs/COMMANDS.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)

### Community
- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - Q&A and general discussion (coming soon)
- **Code Review** - PR reviews and feedback

### Maintainer Contact
For questions about contributing, please:
1. Check existing documentation
2. Search existing GitHub issues
3. Create a new issue with the "question" label
4. For security issues, see [SECURITY.md](SECURITY.md)

## 🎯 Project Goals

### Mission
Provide comprehensive, respectful data collection and analysis tools for U.S. Catholic dioceses and parishes, supporting research and community understanding.

### Technical Goals
- **Respectful automation** that honors website policies
- **High-quality data** with comprehensive validation
- **Scalable architecture** supporting distributed processing
- **Developer-friendly** tools and documentation
- **Production-ready** reliability and monitoring

### Community Goals
- **Open source collaboration** welcoming diverse contributors
- **Educational value** for web scraping and data analysis
- **Ethical standards** in automated data collection
- **Knowledge sharing** about Catholic institutional data

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- Contributors who help improve the project
- The Catholic community for providing publicly accessible data
- Open source libraries that make this project possible
- Google AI for Gemini API access
- Supabase for database infrastructure

---

**Questions?** Feel free to ask in a GitHub issue or check our [documentation](docs/).

**Ready to contribute?** We're excited to see what you'll build! 🚀