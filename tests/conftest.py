"""
Pytest configuration and shared fixtures for Diocesan Vitality tests.

This module provides test configuration, markers, and reusable fixtures
for the entire test suite.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "database: marks tests that require database connection")
    config.addinivalue_line("markers", "api: marks tests that test API endpoints")
    config.addinivalue_line("markers", "integration: marks tests that test component integration")
    config.addinivalue_line("markers", "performance: marks tests that measure performance")
    config.addinivalue_line("markers", "external: marks tests that require external services")


@pytest.fixture(scope="session", autouse=True)
def test_environment():
    """Set up test environment variables."""
    # Set testing flag
    os.environ["TESTING"] = "true"

    # Mock sensitive environment variables if not set
    test_env_vars = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_supabase_key",
        "GENAI_API_KEY": "test_genai_key",
        "SEARCH_API_KEY": "test_search_key",
        "SEARCH_CX": "test_search_cx",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
    }

    original_values = {}
    for key, value in test_env_vars.items():
        if key not in os.environ:
            original_values[key] = None
            os.environ[key] = value
        else:
            original_values[key] = os.environ[key]

    yield

    # Restore original environment
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_parish_data():
    """Provide sample parish data for tests."""
    return {
        "id": 1,
        "name": "Test Parish",
        "address": "123 Test Street",
        "city": "Test City",
        "state": "TS",
        "zip_code": "12345",
        "phone": "(555) 123-4567",
        "email": "test@testparish.org",
        "website_url": "https://testparish.org",
        "diocese_id": 1,
    }


@pytest.fixture
def sample_diocese_data():
    """Provide sample diocese data for tests."""
    return {
        "id": 1,
        "name": "Test Diocese",
        "state": "Test State",
        "website_url": "https://testdiocese.org",
        "parishes_directory_url": "https://testdiocese.org/parishes",
    }


@pytest.fixture
def mock_database():
    """Provide a mock database connection."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock common database operations
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.execute.return_value = None

    with patch("core.db.get_db_connection", return_value=mock_conn):
        yield mock_conn


@pytest.fixture
def mock_webdriver():
    """Provide a mock WebDriver for tests."""
    mock_driver = Mock()

    # Mock common WebDriver operations
    mock_driver.get.return_value = None
    mock_driver.page_source = "<html><body>Test Page</body></html>"
    mock_driver.current_url = "https://test.example.com"
    mock_driver.title = "Test Page"

    # Mock element finding
    mock_element = Mock()
    mock_element.text = "Test Element"
    mock_element.get_attribute.return_value = "test_value"
    mock_driver.find_element.return_value = mock_element
    mock_driver.find_elements.return_value = [mock_element]

    with patch("selenium.webdriver.Chrome", return_value=mock_driver):
        yield mock_driver


@pytest.fixture
def mock_ai_service():
    """Provide a mock AI service for tests."""
    mock_response = {
        "content": "Test AI response",
        "confidence": 0.95,
        "extracted_data": {"parish_name": "AI Extracted Parish", "address": "AI Extracted Address", "phone": "(555) 987-6543"},
    }

    with patch("core.ai_content_analyzer.analyze_content", return_value=mock_response):
        yield mock_response


@pytest.fixture
def mock_http_response():
    """Provide a mock HTTP response for tests."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.content = b"<html><body>Test Content</body></html>"
    mock_response.text = "<html><body>Test Content</body></html>"
    mock_response.url = "https://test.example.com"

    return mock_response


@pytest.fixture
def circuit_breaker_config():
    """Provide circuit breaker configuration for tests."""
    return {"failure_threshold": 3, "success_threshold": 2, "timeout": 10, "expected_exception": Exception}


@pytest.fixture
def test_logger():
    """Provide a test logger that captures log messages."""
    import logging
    from io import StringIO

    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    yield logger, log_capture

    # Clean up
    logger.removeHandler(handler)


# Test data fixtures for specific components
@pytest.fixture
def sample_mass_schedule():
    """Provide sample mass schedule data."""
    return {
        "parish_id": 1,
        "day_of_week": "Sunday",
        "time": "09:00:00",
        "mass_type": "Regular",
        "language": "English",
        "special_notes": "Family Mass",
    }


@pytest.fixture
def sample_extraction_result():
    """Provide sample extraction result data."""
    return {
        "success": True,
        "parish_data": {"name": "Extracted Parish", "address": "456 Extracted Ave", "phone": "(555) 456-7890"},
        "extraction_time": 2.5,
        "source_url": "https://extractedparish.org",
        "extraction_method": "ai_analysis",
    }


@pytest.fixture
def performance_benchmark():
    """Provide performance benchmarking utilities."""
    import time
    from contextlib import contextmanager

    @contextmanager
    def measure_time():
        start_time = time.time()
        yield
        end_time = time.time()
        execution_time = end_time - start_time
        # Store the result for assertion
        measure_time.last_execution_time = execution_time

    measure_time.last_execution_time = 0
    return measure_time


# Skip markers for conditional test execution
def pytest_runtest_setup(item):
    """Skip tests based on environment conditions."""
    # Skip database tests if no database available
    if "database" in item.keywords:
        try:
            # Try to import database utilities
            from core.db import get_db_connection

            conn = get_db_connection()
            if conn:
                conn.close()
        except Exception:
            pytest.skip("Database not available for testing")

    # Skip external tests if running in CI without credentials
    if "external" in item.keywords:
        if os.getenv("CI") and not os.getenv("EXTERNAL_TEST_CREDENTIALS"):
            pytest.skip("External service credentials not available in CI")


# Custom assertions
def assert_valid_parish_data(parish_data):
    """Assert that parish data contains required fields."""
    required_fields = ["name", "address", "city", "state"]
    for field in required_fields:
        assert field in parish_data, f"Missing required field: {field}"
        assert parish_data[field], f"Empty required field: {field}"


def assert_valid_extraction_result(result):
    """Assert that extraction result has valid structure."""
    assert "success" in result
    assert "parish_data" in result
    assert "extraction_time" in result
    assert isinstance(result["success"], bool)
    assert isinstance(result["extraction_time"], (int, float))


# Make custom assertions available to all tests
pytest.assert_valid_parish_data = assert_valid_parish_data
pytest.assert_valid_extraction_result = assert_valid_extraction_result
