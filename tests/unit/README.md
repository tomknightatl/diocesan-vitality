# Unit Tests

This directory contains unit tests for individual components of the Diocesan Vitality system.

## 📁 Structure

```
unit/
├── core/                   # Tests for core utilities
│   ├── test_circuit_breaker.py
│   ├── test_database.py
│   ├── test_logger.py
│   └── test_utils.py
├── extractors/             # Tests for extraction logic
│   ├── test_parish_extractors.py
│   ├── test_ai_analyzer.py
│   └── test_url_predictor.py
├── pipeline/               # Tests for pipeline components
│   ├── test_runner.py
│   ├── test_extractor.py
│   └── test_coordinator.py
└── cli/                    # Tests for CLI functionality
    ├── test_main.py
    └── test_commands.py
```

## 🎯 Unit Test Guidelines

### Characteristics
- **Fast execution** (< 1 second per test)
- **Isolated** (no external dependencies)
- **Deterministic** (same input always produces same output)
- **Focused** (tests single function or method)

### Naming Convention
```python
def test_function_name_expected_behavior():
    """Test that function_name behaves as expected under normal conditions."""
    pass

def test_function_name_with_invalid_input_raises_error():
    """Test that function_name raises appropriate error with invalid input."""
    pass

def test_function_name_edge_case_returns_default():
    """Test that function_name handles edge case appropriately."""
    pass
```

### Test Structure
```python
def test_example():
    # Arrange - Set up test data
    input_data = create_test_data()
    expected_result = "expected_value"

    # Act - Execute function under test
    actual_result = function_under_test(input_data)

    # Assert - Verify results
    assert actual_result == expected_result
```

## 🧪 Test Examples

### Testing Core Utilities
```python
def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after configured number of failures."""
    cb = CircuitBreaker(failure_threshold=3)

    # Simulate failures
    for _ in range(3):
        cb.record_failure()

    assert cb.state == "OPEN"
```

### Testing Extractors
```python
def test_parish_extractor_parses_valid_html():
    """Test parish extractor correctly parses valid HTML."""
    html_content = "<h1>Test Parish</h1><p>123 Test St</p>"
    extractor = ParishExtractor()

    result = extractor.extract_from_html(html_content)

    assert result["name"] == "Test Parish"
    assert "123 Test St" in result["address"]
```

### Mocking External Dependencies
```python
@patch('requests.get')
def test_http_client_handles_timeout(mock_get):
    """Test HTTP client handles timeout gracefully."""
    mock_get.side_effect = requests.Timeout("Connection timeout")
    client = HttpClient()

    result = client.fetch_url("https://example.com")

    assert result is None
    assert client.last_error == "timeout"
```

## 🚀 Running Unit Tests

### All Unit Tests
```bash
pytest tests/unit/
```

### Specific Component
```bash
pytest tests/unit/core/
pytest tests/unit/extractors/
pytest tests/unit/pipeline/
pytest tests/unit/cli/
```

### Single Test File
```bash
pytest tests/unit/core/test_circuit_breaker.py
```

### Single Test Function
```bash
pytest tests/unit/core/test_circuit_breaker.py::test_circuit_breaker_opens_after_failures
```

### With Coverage
```bash
pytest tests/unit/ --cov=src/diocesan_vitality --cov-report=term-missing
```

## 📊 Coverage Goals

- **Core utilities**: 95%+ coverage
- **Business logic**: 90%+ coverage
- **Error handling**: 85%+ coverage
- **Integration points**: 80%+ coverage

## 🔧 Common Patterns

### Testing Exceptions
```python
def test_function_raises_value_error_for_negative_input():
    """Test function raises ValueError for negative input."""
    with pytest.raises(ValueError, match="Input must be positive"):
        function_under_test(-1)
```

### Testing with Fixtures
```python
def test_parser_with_sample_data(sample_parish_data):
    """Test parser with sample parish data."""
    parser = ParishDataParser()
    result = parser.parse(sample_parish_data)
    assert result.is_valid
```

### Parameterized Tests
```python
@pytest.mark.parametrize("input_value,expected", [
    ("test@example.com", True),
    ("invalid-email", False),
    ("", False),
])
def test_email_validation(input_value, expected):
    """Test email validation with various inputs."""
    assert validate_email(input_value) == expected
```

### Testing Async Functions
```python
@pytest.mark.asyncio
async def test_async_extractor():
    """Test async extraction functionality."""
    extractor = AsyncParishExtractor()
    result = await extractor.extract_parish_data("https://example.com")
    assert result is not None
```

## 🐛 Debugging Unit Tests

### Verbose Output
```bash
pytest tests/unit/ -v
```

### Stop on First Failure
```bash
pytest tests/unit/ -x
```

### Debug on Failure
```bash
pytest tests/unit/ --pdb
```

### Show Print Statements
```bash
pytest tests/unit/ -s
```

## 📚 Related Documentation

- **[Test Configuration](../conftest.py)** - Shared fixtures and configuration
- **[Integration Tests](../integration/README.md)** - Component integration testing
- **[Performance Tests](../performance/README.md)** - Performance and load testing