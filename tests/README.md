# Test Suite

This directory contains the comprehensive test suite for the Diocesan Vitality project.

## 📁 Test Organization

### Test Categories

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── core/               # Tests for core utilities
│   ├── extractors/         # Tests for extraction logic
│   ├── pipeline/           # Tests for pipeline components
│   └── cli/                # Tests for CLI functionality
├── integration/            # Integration tests
│   ├── database/           # Database integration tests
│   ├── api/                # API integration tests
│   └── pipeline/           # End-to-end pipeline tests
├── performance/            # Performance and load tests
├── fixtures/               # Test data and fixtures
└── conftest.py            # Pytest configuration and shared fixtures
```

## 🚀 Running Tests

### Quick Testing
```bash
# Run all tests
pytest

# Run quick unit tests only
make test-quick

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/core/test_circuit_breaker.py
```

### Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Performance tests
pytest tests/performance/

# Tests by component
pytest tests/unit/core/
pytest tests/unit/extractors/
pytest tests/integration/database/
```

### Test Selection
```bash
# Run tests matching pattern
pytest -k "test_circuit_breaker"

# Run tests with specific markers
pytest -m "slow"
pytest -m "database"
pytest -m "api"

# Run failed tests from last run
pytest --lf
```

## 🏗️ Test Structure

### Unit Tests
Test individual functions and classes in isolation:
- **Fast execution** (< 1 second per test)
- **No external dependencies** (database, network, filesystem)
- **Mock external services** and dependencies
- **High coverage** of business logic

### Integration Tests
Test component interactions and external services:
- **Database operations** with test database
- **API endpoints** and responses
- **File system operations** with temporary directories
- **External service integrations** (with test credentials)

### Performance Tests
Test system performance and resource usage:
- **Load testing** with multiple concurrent users
- **Memory usage** monitoring
- **Response time** measurements
- **Scalability** testing

## 🛠️ Test Configuration

### Environment Setup
Tests use a separate test environment:
```bash
# Test environment variables
TESTING=true
DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/test_db
GENAI_API_KEY=test_key_for_testing
```

### Test Database
Integration tests use a dedicated test database:
- **Isolated from production** data
- **Reset between test runs** for consistency
- **Minimal test data** for fast execution
- **Schema matches production** for accuracy

### Fixtures and Mocks
Common test utilities:
- **Database fixtures** with sample data
- **Mock services** for external APIs
- **Test clients** for API testing
- **Temporary directories** for file operations

## 📊 Test Coverage

### Coverage Goals
- **Unit tests**: 90%+ coverage of business logic
- **Integration tests**: Critical paths and API endpoints
- **End-to-end tests**: Main user workflows

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Generate terminal coverage report
pytest --cov=src --cov-report=term-missing

# Check coverage minimums
pytest --cov=src --cov-fail-under=80
```

## 🔧 Writing Tests

### Test Naming Convention
```python
# Unit test example
def test_circuit_breaker_opens_on_failures():
    """Test that circuit breaker opens after configured failures."""
    pass

# Integration test example
def test_database_stores_parish_data():
    """Test that parish data is correctly stored in database."""
    pass

# Performance test example
def test_extraction_performance_under_load():
    """Test extraction performance with multiple concurrent requests."""
    pass
```

### Test Structure (AAA Pattern)
```python
def test_example():
    # Arrange - Set up test data and conditions
    extractor = ParishExtractor()
    mock_response = create_mock_response()

    # Act - Execute the functionality being tested
    result = extractor.extract_parish_data(mock_response)

    # Assert - Verify the expected outcomes
    assert result.name == "Expected Parish Name"
    assert result.address is not None
```

### Using Fixtures
```python
@pytest.fixture
def sample_parish_data():
    """Provide sample parish data for tests."""
    return {
        "name": "Test Parish",
        "address": "123 Test St",
        "city": "Test City",
        "state": "TS"
    }

def test_parish_validation(sample_parish_data):
    """Test parish data validation."""
    validator = ParishValidator()
    result = validator.validate(sample_parish_data)
    assert result.is_valid
```

## 🏷️ Test Markers

### Available Markers
```python
# Mark slow tests
@pytest.mark.slow
def test_full_pipeline_execution():
    pass

# Mark database tests
@pytest.mark.database
def test_database_operations():
    pass

# Mark API tests
@pytest.mark.api
def test_api_endpoints():
    pass

# Mark integration tests
@pytest.mark.integration
def test_component_integration():
    pass

# Mark performance tests
@pytest.mark.performance
def test_extraction_performance():
    pass
```

### Running Specific Markers
```bash
# Skip slow tests during development
pytest -m "not slow"

# Run only database tests
pytest -m "database"

# Run API and integration tests
pytest -m "api or integration"
```

## 🐛 Debugging Tests

### Debug Commands
```bash
# Run with verbose output
pytest -v

# Run with extra verbose output
pytest -vv

# Stop on first failure
pytest -x

# Drop into debugger on failures
pytest --pdb

# Show local variables on failures
pytest --tb=long

# Run single test with debugging
pytest tests/unit/core/test_circuit_breaker.py::test_specific_function -vv --pdb
```

### Common Issues
1. **Import errors**: Check PYTHONPATH and project structure
2. **Database connection**: Verify test database is running
3. **Environment variables**: Ensure test environment is configured
4. **Mock failures**: Verify mock objects match real service interfaces

## 📈 Continuous Integration

### GitHub Actions
Tests run automatically on:
- **Pull requests** to main/develop branches
- **Push to main** branch
- **Daily scheduled runs** for regression testing

### Test Stages
1. **Code quality** (linting, formatting)
2. **Unit tests** (fast, no external dependencies)
3. **Integration tests** (with test database)
4. **Performance tests** (on main branch only)

### Test Reports
- **Coverage reports** uploaded to Codecov
- **Test results** displayed in PR checks
- **Performance metrics** tracked over time

## 🔄 Test Data Management

### Test Fixtures
Located in `tests/fixtures/`:
- **Sample responses** from parish websites
- **Database seed data** for consistent testing
- **Configuration files** for test environments

### Data Cleanup
Tests automatically:
- **Reset database** state between runs
- **Clean temporary files** after execution
- **Restore mocked services** to original state

## 📚 Related Documentation

- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute tests
- **[Local Development](../docs/LOCAL_DEVELOPMENT.md)** - Development environment setup
- **[CI/CD Pipeline](../docs/CI_CD_PIPELINE.md)** - Automated testing pipeline

## 🆘 Getting Help

If you encounter issues with tests:
1. Check the [troubleshooting section](../docs/LOCAL_DEVELOPMENT.md#troubleshooting)
2. Review recent [GitHub issues](https://github.com/tomknightatl/diocesan-vitality/issues)
3. Ask questions in [GitHub Discussions](https://github.com/tomknightatl/diocesan-vitality/discussions)
4. Create a new issue with test output and environment details