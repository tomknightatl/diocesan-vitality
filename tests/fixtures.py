#!/usr/bin/env python3
"""
Comprehensive test fixtures for diocesan vitality testing.

This module provides consistent, reusable test data and fixtures
to improve test reliability and reduce duplication across the test suite.
"""

from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest


class TestDataFixtures:
    """Centralized test data fixtures for consistent testing."""

    @staticmethod
    def sample_diocese_data() -> Dict[str, Any]:
        """Standard diocese test data."""
        return {
            "id": 1,
            "name": "Test Diocese of Sample City",
            "state": "Test State",
            "website_url": "https://testdiocese.org",
            "parishes_directory_url": "https://testdiocese.org/parishes",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_blocked": False,
            "respectful_automation_used": True,
            "status_description": "Active for testing",
        }

    @staticmethod
    def sample_parish_data() -> Dict[str, Any]:
        """Standard parish test data."""
        return {
            "id": 1,
            "name": "St. Test Parish",
            "address": "123 Test Avenue",
            "city": "Test City",
            "state": "TS",
            "zip_code": "12345",
            "phone": "(555) 123-4567",
            "email": "contact@sttestparish.org",
            "website_url": "https://sttestparish.org",
            "diocese_id": 1,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "extraction_status": "completed",
            "extraction_method": "ai_analysis",
        }

    @staticmethod
    def sample_mass_schedule_data() -> Dict[str, Any]:
        """Standard mass schedule test data."""
        return {
            "id": 1,
            "parish_id": 1,
            "day_of_week": "Sunday",
            "time": "09:00:00",
            "mass_type": "Regular",
            "language": "English",
            "special_notes": "Family Mass with Children's Liturgy",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    @staticmethod
    def sample_extraction_result() -> Dict[str, Any]:
        """Standard extraction result test data."""
        return {
            "success": True,
            "parishes_found": 5,
            "parishes_processed": 5,
            "parishes_with_errors": 0,
            "extraction_time": 2.5,
            "source_url": "https://testdiocese.org/parishes",
            "extraction_method": "ai_analysis",
            "timestamp": datetime.now().isoformat(),
            "error_details": [],
            "performance_metrics": {
                "avg_time_per_parish": 0.5,
                "total_http_requests": 10,
                "cache_hit_rate": 0.8,
            },
        }

    @staticmethod
    def multiple_parishes_data(count: int = 10) -> List[Dict[str, Any]]:
        """Generate multiple parish test records."""
        parishes = []
        base_parish = TestDataFixtures.sample_parish_data()

        for i in range(count):
            parish = base_parish.copy()
            parish.update(
                {
                    "id": i + 1,
                    "name": f"St. Test Parish {i + 1}",
                    "address": f"{100 + i} Test Street",
                    "email": f"parish{i + 1}@testdiocese.org",
                    "website_url": f"https://parish{i + 1}.testdiocese.org",
                    "phone": f"(555) 123-{4567 + i}",
                }
            )
            parishes.append(parish)

        return parishes

    @staticmethod
    def sample_worker_status() -> Dict[str, Any]:
        """Standard worker status test data."""
        return {
            "worker_id": "test-worker-001",
            "worker_type": "extraction",
            "status": "active",
            "current_task": "processing_diocese_1",
            "parishes_processed": 25,
            "parishes_remaining": 15,
            "start_time": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "performance_metrics": {
                "avg_processing_time": 1.2,
                "success_rate": 0.95,
                "error_count": 2,
            },
        }

    @staticmethod
    def sample_error_data() -> Dict[str, Any]:
        """Standard error test data."""
        return {
            "error_type": "extraction_error",
            "error_message": "Failed to parse parish directory page",
            "error_code": "PARSE_ERROR_001",
            "url": "https://testparish.org/directory",
            "timestamp": datetime.now().isoformat(),
            "retry_count": 2,
            "max_retries": 3,
            "context": {
                "diocese_id": 1,
                "parish_name": "St. Test Parish",
                "extraction_method": "css_selectors",
            },
        }


@pytest.fixture
def diocese_data():
    """Pytest fixture for diocese test data."""
    return TestDataFixtures.sample_diocese_data()


@pytest.fixture
def parish_data():
    """Pytest fixture for parish test data."""
    return TestDataFixtures.sample_parish_data()


@pytest.fixture
def mass_schedule_data():
    """Pytest fixture for mass schedule test data."""
    return TestDataFixtures.sample_mass_schedule_data()


@pytest.fixture
def extraction_result():
    """Pytest fixture for extraction result test data."""
    return TestDataFixtures.sample_extraction_result()


@pytest.fixture
def multiple_parishes():
    """Pytest fixture for multiple parish test data."""
    return TestDataFixtures.multiple_parishes_data(5)


@pytest.fixture
def worker_status():
    """Pytest fixture for worker status test data."""
    return TestDataFixtures.sample_worker_status()


@pytest.fixture
def error_data():
    """Pytest fixture for error test data."""
    return TestDataFixtures.sample_error_data()


@pytest.fixture
def mock_database_responses():
    """Pytest fixture for mock database responses."""
    return {
        "dioceses": TestDataFixtures.multiple_parishes_data(3),
        "parishes": TestDataFixtures.multiple_parishes_data(10),
        "mass_schedules": [TestDataFixtures.sample_mass_schedule_data()],
        "workers": [TestDataFixtures.sample_worker_status()],
    }


@pytest.fixture
def mock_webdriver():
    """Enhanced mock WebDriver fixture."""
    mock_driver = Mock()

    # Mock common WebDriver operations
    mock_driver.get.return_value = None
    mock_driver.quit.return_value = None
    mock_driver.close.return_value = None
    mock_driver.current_url = "https://test.example.com"
    mock_driver.title = "Test Page Title"
    mock_driver.page_source = """
    <html>
        <body>
            <div class="parish-list">
                <div class="parish-item">
                    <h3>St. Test Parish</h3>
                    <p>123 Test Street, Test City, TS 12345</p>
                    <p>Phone: (555) 123-4567</p>
                    <a href="mailto:contact@sttestparish.org">contact@sttestparish.org</a>
                </div>
            </div>
        </body>
    </html>
    """

    # Mock element finding
    mock_element = Mock()
    mock_element.text = "St. Test Parish"
    mock_element.get_attribute.return_value = "https://sttestparish.org"
    mock_element.is_displayed.return_value = True

    mock_driver.find_element.return_value = mock_element
    mock_driver.find_elements.return_value = [mock_element]

    return mock_driver


@pytest.fixture
def mock_ai_response():
    """Mock AI service response fixture."""
    return {
        "analysis_result": {
            "confidence": 0.92,
            "extracted_parishes": [
                {
                    "name": "St. AI Extracted Parish",
                    "address": "456 AI Street, AI City, AI 67890",
                    "phone": "(555) 987-6543",
                    "email": "ai@extracted.org",
                    "website": "https://aiextracted.org",
                }
            ],
            "custom_selectors": [
                ".parish-directory .parish-card",
                ".church-listing h3",
                ".contact-info a[href*='mailto']",
            ],
            "extraction_strategy": "css_selectors_with_ai_validation",
            "processing_time": 1.8,
        }
    }


@pytest.fixture
def performance_baseline():
    """Performance baseline expectations for regression testing."""
    return {
        "circuit_breaker_overhead": 0.01,  # seconds per 1000 calls
        "logger_performance": 0.1,  # seconds per 1000 log messages
        "parish_processing": 0.1,  # seconds per 100 parishes (mock)
        "import_time": 0.1,  # seconds for critical imports
        "config_loading": 0.001,  # seconds for configuration loading
        "memory_per_circuit_breaker": 1024,  # bytes per circuit breaker
        "concurrent_operations": 1.0,  # seconds for concurrent tests
    }


class MockHTTPResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code=200, content="", headers=None):
        self.status_code = status_code
        self.content = content.encode() if isinstance(content, str) else content
        self.text = content if isinstance(content, str) else content.decode()
        self.headers = headers or {"Content-Type": "text/html"}
        self.url = "https://test.example.com"

    def json(self):
        """Mock JSON response."""
        import json

        return json.loads(self.text)

    def raise_for_status(self):
        """Mock raise for status."""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")


@pytest.fixture
def mock_http_responses():
    """Mock HTTP responses fixture."""
    return {
        "success": MockHTTPResponse(200, "<html><body>Test Content</body></html>"),
        "not_found": MockHTTPResponse(404, "Not Found"),
        "server_error": MockHTTPResponse(500, "Internal Server Error"),
        "parish_directory": MockHTTPResponse(
            200,
            """
            <html>
                <body>
                    <div class="parish-directory">
                        <div class="parish-card">
                            <h3>St. Test Parish 1</h3>
                            <p>123 Test St, Test City, TS 12345</p>
                        </div>
                        <div class="parish-card">
                            <h3>St. Test Parish 2</h3>
                            <p>456 Test Ave, Test City, TS 12346</p>
                        </div>
                    </div>
                </body>
            </html>
            """,
        ),
    }


if __name__ == "__main__":
    # Demonstrate fixture usage
    print("Sample Diocese Data:")
    print(TestDataFixtures.sample_diocese_data())
    print("\nSample Parish Data:")
    print(TestDataFixtures.sample_parish_data())
    print("\nMultiple Parishes (3):")
    for parish in TestDataFixtures.multiple_parishes_data(3):
        print(f"  - {parish['name']}: {parish['address']}")
