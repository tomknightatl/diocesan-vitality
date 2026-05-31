#!/usr/bin/env python3
"""
Test script for AI authentication and configuration system.

This script tests the three core components:
1. AI Configuration Management
2. AI Authentication Manager
3. AI Model Factory

Run with: python tests/test_ai_system.py
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ai_config import AIConfig, get_ai_config, reset_ai_config
from core.ai_auth_manager import (
    AIAuthManager,
    get_ai_auth_manager,
    reset_ai_auth_manager,
    APIKeyAuthStrategy,
    OAuthAuthStrategy,
    ServiceAccountAuthStrategy,
    AutoDetectAuthStrategy,
)
from core.ai_model_factory import (
    AIModelFactory,
    get_ai_model_factory,
    reset_ai_model_factory,
)
from core.logger import get_logger

logger = get_logger(__name__)


def test_ai_config():
    """Test AI configuration management."""
    print("\n" + "="*60)
    print("Testing AI Configuration Management")
    print("="*60)

    try:
        # Reset global config
        reset_ai_config()

        # Test default configuration
        config = get_ai_config()
        print(f"✓ Default config loaded")
        print(f"  - Auth method: {config.auth_method}")
        print(f"  - Default model: {config.default_model}")
        print(f"  - Enable caching: {config.enable_caching}")

        # Test component-specific models
        content_model = config.get_model_for_component("content_analyzer")
        schedule_model = config.get_model_for_component("schedule_extractor")
        print(f"✓ Component models retrieved")
        print(f"  - Content analyzer: {content_model}")
        print(f"  - Schedule extractor: {schedule_model}")

        # Test model parameters
        params = config.model_parameters
        print(f"✓ Model parameters retrieved")
        print(f"  - Temperature: {params['temperature']}")
        print(f"  - Max tokens: {params['max_tokens']}")

        # Test all component models
        all_models = config.get_all_component_models()
        print(f"✓ All component models retrieved ({len(all_models)} components)")

        print("\n✅ AI Configuration tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ AI Configuration tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth_strategies():
    """Test individual authentication strategies."""
    print("\n" + "="*60)
    print("Testing Authentication Strategies")
    print("="*60)

    try:
        # Test API Key Strategy
        print("\n1. Testing API Key Strategy...")
        api_key_strategy = APIKeyAuthStrategy()
        print(f"  - API key present: {api_key_strategy.api_key is not None}")
        if api_key_strategy.api_key:
            if api_key_strategy.authenticate():
                print(f"  ✓ API key authentication successful")
            else:
                print(f"  ⚠ API key authentication failed (may be invalid)")
        else:
            print(f"  ⚠ API key not found (set GENAI_API_KEY env var)")

        # Test OAuth Strategy
        print("\n2. Testing OAuth Strategy...")
        oauth_strategy = OAuthAuthStrategy()
        if oauth_strategy.authenticate():
            print(f"  ✓ OAuth authentication successful")
        else:
            print(f"  ⚠ OAuth authentication failed (no ADC available)")

        # Test Service Account Strategy
        print("\n3. Testing Service Account Strategy...")
        sa_strategy = ServiceAccountAuthStrategy()
        if sa_strategy.authenticate():
            print(f"  ✓ Service account authentication successful")
        else:
            print(f"  ⚠ Service account authentication failed (no credentials file)")

        # Test Auto-Detect Strategy
        print("\n4. Testing Auto-Detect Strategy...")
        auto_strategy = AutoDetectAuthStrategy()
        if auto_strategy.authenticate():
            print(f"  ✓ Auto-detect authentication successful")
            print(f"  - Active strategy: {auto_strategy.active_strategy_name}")
        else:
            print(f"  ⚠ Auto-detect authentication failed (no credentials available)")

        print("\n✅ Authentication Strategy tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Authentication Strategy tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth_manager():
    """Test AI authentication manager."""
    print("\n" + "="*60)
    print("Testing AI Authentication Manager")
    print("="*60)

    try:
        # Reset global auth manager
        reset_ai_auth_manager()

        # Test with auto-detect
        print("\n1. Testing with auto-detect method...")
        auth_manager = get_ai_auth_manager(auth_method="auto_detect")
        if auth_manager.authenticate():
            print(f"  ✓ Authentication successful")
            print(f"  - Method: {auth_manager.auth_method}")
            print(f"  - Active strategy: {auth_manager.active_strategy_name}")
        else:
            print(f"  ⚠ Authentication failed (no credentials available)")

        # Test genai configuration
        print("\n2. Testing genai configuration...")
        if auth_manager.configure_genai():
            print(f"  ✓ genai configured successfully")
        else:
            print(f"  ⚠ genai configuration failed")

        # Test credentials refresh
        print("\n3. Testing credentials refresh...")
        if auth_manager.refresh_credentials():
            print(f"  ✓ Credentials refreshed successfully")
        else:
            print(f"  ⚠ Credentials refresh failed")

        print("\n✅ Authentication Manager tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Authentication Manager tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_factory():
    """Test AI model factory."""
    print("\n" + "="*60)
    print("Testing AI Model Factory")
    print("="*60)

    try:
        # Reset global factory
        reset_ai_model_factory()

        # Create factory
        print("\n1. Creating model factory...")
        factory = get_ai_model_factory()
        print(f"  ✓ Factory created")

        # Test model capabilities
        print("\n2. Testing model capabilities...")
        capabilities = factory.get_model_capabilities("gemini-1.5-flash")
        print(f"  ✓ Capabilities retrieved")
        print(f"  - Max tokens: {capabilities['max_tokens']}")
        print(f"  - Supports vision: {capabilities['supports_vision']}")

        # Test model metadata
        print("\n3. Testing model metadata...")
        metadata = factory.get_model_metadata("gemini-1.5-flash")
        print(f"  ✓ Metadata retrieved")
        print(f"  - Name: {metadata['name']}")
        print(f"  - Is known: {metadata['is_known']}")

        # Test listing models
        print("\n4. Testing list available models...")
        try:
            models = factory.list_available_models()
            print(f"  ✓ Available models: {len(models)}")
            for model in models[:5]:  # Show first 5
                print(f"    - {model}")
        except Exception as e:
            print(f"  ⚠ Could not list models: {e}")

        # Test cache stats
        print("\n5. Testing cache stats...")
        stats = factory.get_cache_stats()
        print(f"  ✓ Cache stats retrieved")
        print(f"  - Total entries: {stats['total_entries']}")
        print(f"  - Cache enabled: {stats['cache_enabled']}")

        # Test model creation (only if authenticated)
        print("\n6. Testing model creation...")
        try:
            model = factory.get_model("content_analyzer")
            print(f"  ✓ Model created successfully")
            print(f"  - Model name: {model.model_name}")

            # Test simple generation
            print("\n7. Testing simple generation...")
            response = model.generate_content("Say 'Hello, World!'")
            if response and response.text:
                print(f"  ✓ Generation successful")
                print(f"  - Response: {response.text[:50]}...")
            else:
                print(f"  ⚠ Generation returned empty response")

        except Exception as e:
            print(f"  ⚠ Model creation failed (authentication may be required): {e}")

        print("\n✅ Model Factory tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Model Factory tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test full integration of all components."""
    print("\n" + "="*60)
    print("Testing Full Integration")
    print("="*60)

    try:
        # Reset all globals
        reset_ai_config()
        reset_ai_auth_manager()
        reset_ai_model_factory()

        print("\n1. Setting up configuration...")
        config = get_ai_config()
        print(f"  ✓ Config loaded")

        print("\n2. Setting up authentication...")
        auth_manager = get_ai_auth_manager(auth_method="auto_detect")
        if auth_manager.authenticate():
            print(f"  ✓ Authenticated with {auth_manager.active_strategy_name}")
        else:
            print(f"  ⚠ Authentication failed")

        print("\n3. Setting up model factory...")
        factory = get_ai_model_factory(config=config, auth_manager=auth_manager)
        print(f"  ✓ Factory created")

        print("\n4. Getting models for different components...")
        components = ["content_analyzer", "schedule_extractor", "fallback_extractor"]
        for component in components:
            try:
                model = factory.get_model(component)
                print(f"  ✓ {component}: {model.model_name}")
            except Exception as e:
                print(f"  ⚠ {component}: Failed - {e}")

        print("\n5. Testing cache operations...")
        factory.clear_cache()
        stats = factory.get_cache_stats()
        print(f"  ✓ Cache cleared, entries: {stats['total_entries']}")

        print("\n✅ Integration tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Integration tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("AI Authentication and Configuration System Tests")
    print("="*60)

    results = []

    # Run all tests
    results.append(("AI Configuration", test_ai_config()))
    results.append(("Auth Strategies", test_auth_strategies()))
    results.append(("Auth Manager", test_auth_manager()))
    results.append(("Model Factory", test_model_factory()))
    results.append(("Integration", test_integration()))

    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())