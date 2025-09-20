"""
Core functionality tests for the diocesan vitality pipeline.
"""
import sys
import os
import pytest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_core_imports():
    """Test that core modules can be imported successfully."""
    try:
        import core.logger
        import core.db_batch_operations
        import core.circuit_breaker
        assert True
    except ImportError as e:
        pytest.fail(f"Core imports failed: {e}")


def test_logger_initialization():
    """Test logger module can be initialized."""
    from core.logger import get_logger

    logger = get_logger("test")
    assert logger is not None
    assert logger.name == "test"


def test_circuit_breaker_config():
    """Test circuit breaker configuration."""
    try:
        from core.circuit_breaker import CircuitBreakerConfig

        config = CircuitBreakerConfig()
        assert config.failure_threshold > 0
        assert config.recovery_timeout > 0
    except ImportError:
        pytest.skip("Circuit breaker module not available")


def test_environment_setup():
    """Test that testing environment is properly configured."""
    # Check if we're in testing mode
    testing_mode = os.getenv('TESTING', 'false').lower()
    assert testing_mode in ['true', 'false']

    # Test basic Python environment
    assert sys.version_info >= (3, 8), "Python 3.8+ required"


def test_database_batch_operations_import():
    """Test database batch operations module import."""
    try:
        from core.db_batch_operations import DatabaseBatchManager
        assert DatabaseBatchManager is not None
    except ImportError:
        pytest.skip("Database batch operations module not available")


@pytest.mark.asyncio
async def test_async_functionality():
    """Test that async functionality works correctly."""
    import asyncio

    async def dummy_async():
        await asyncio.sleep(0.001)  # Minimal async operation
        return "success"

    result = await dummy_async()
    assert result == "success"


def test_project_structure():
    """Test that expected project directories exist."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    expected_dirs = [
        'core',
        'extractors',
        'backend',
        'frontend',
        'k8s',
        'docs'
    ]

    for expected_dir in expected_dirs:
        dir_path = os.path.join(project_root, expected_dir)
        assert os.path.exists(dir_path), f"Expected directory {expected_dir} not found"


def test_required_files():
    """Test that required configuration files exist."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    required_files = [
        'requirements.txt',
        'README.md',
        '.env.example'
    ]

    for required_file in required_files:
        file_path = os.path.join(project_root, required_file)
        assert os.path.exists(file_path), f"Required file {required_file} not found"
