"""
Integration tests for the diocesan vitality pipeline.
"""

import os
import sys

import pytest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_environment_variables():
    """Test that required environment variables are available."""
    # Core testing variables
    assert os.getenv("TESTING") is not None

    # Optional variables (should not fail if missing in test environment)
    env_vars_to_check = ["SUPABASE_URL", "SUPABASE_KEY", "GENAI_API_KEY"]

    missing_vars = []
    for var in env_vars_to_check:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        pytest.skip(f"Optional environment variables missing: {missing_vars}")


def test_database_connection():
    """Test database connectivity if DATABASE_URL is provided."""
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        pytest.skip("DATABASE_URL not provided - skipping database tests")

    # Basic URL validation
    assert "postgresql" in db_url or "postgres" in db_url

    # Test connection if psycopg2 is available
    try:
        import psycopg2

        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        result = cursor.fetchone()
        assert result[0] == 1
        cursor.close()
        conn.close()
    except ImportError:
        pytest.skip("psycopg2 not available - skipping actual database connection test")
    except Exception as e:
        pytest.fail(f"Database connection failed: {e}")


def test_web_scraping_dependencies():
    """Test that web scraping dependencies are available."""
    required_packages = ["selenium", "beautifulsoup4", "requests"]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        pytest.fail(f"Required packages missing: {missing_packages}")


def test_ai_dependencies():
    """Test that AI/ML dependencies are available."""
    try:
        import google.generativeai

        assert True
    except ImportError:
        pytest.skip("Google GenerativeAI not available")


def test_async_webdriver_capabilities():
    """Test async webdriver functionality if available."""
    try:
        from core.async_driver import AsyncWebDriverPool

        # Basic initialization test (without actually creating drivers)
        pool = AsyncWebDriverPool(pool_size=1)
        assert pool.pool_size == 1
        assert pool.default_timeout == 30

    except ImportError:
        pytest.skip("Async driver module not available")


def test_circuit_breaker_integration():
    """Test circuit breaker integration."""
    try:
        from core.circuit_breaker import CircuitBreakerConfig, circuit_manager

        # Test circuit breaker configuration
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=10)

        assert config.failure_threshold == 3
        assert config.recovery_timeout == 10

    except ImportError:
        pytest.skip("Circuit breaker module not available")


def test_extraction_capabilities():
    """Test that extraction modules are importable."""
    try:
        # Test core extraction modules
        import core.ai_content_analyzer
        import core.extraction_optimizer

        # Test basic extractor imports
        from extractors.enhanced_ai_fallback_extractor import EnhancedAIFallbackExtractor

        assert EnhancedAIFallbackExtractor is not None

    except ImportError as e:
        pytest.skip(f"Extraction modules not fully available: {e}")


def test_monitoring_integration():
    """Test monitoring client integration."""
    try:
        from core.monitoring_client import MonitoringClient

        # Test basic initialization
        client = MonitoringClient("http://localhost:8000")
        assert client.base_url == "http://localhost:8000"

    except ImportError:
        pytest.skip("Monitoring client not available")


@pytest.mark.asyncio
async def test_async_parish_extraction():
    """Test async parish extraction module."""
    try:
        from core.async_parish_extractor import AsyncParishExtractor

        # Basic initialization test
        extractor = AsyncParishExtractor(pool_size=1, batch_size=2)
        assert extractor.pool_size == 1
        assert extractor.batch_size == 2

    except ImportError:
        pytest.skip("Async parish extractor not available")


def test_configuration_loading():
    """Test that configuration can be loaded."""
    try:
        import config

        assert True
    except ImportError:
        pytest.skip("Config module not available")


def test_dockerfile_exists():
    """Test that required Dockerfiles exist."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    dockerfiles = ["backend/Dockerfile", "frontend/Dockerfile", "Dockerfile.pipeline"]

    for dockerfile in dockerfiles:
        path = os.path.join(project_root, dockerfile)
        assert os.path.exists(path), f"Dockerfile not found: {dockerfile}"
