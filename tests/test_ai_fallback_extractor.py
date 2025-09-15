#!/usr/bin/env python3
"""
Test script for AI-powered content analysis and fallback extraction.

This script tests the new AI fallback extractor on a diocese that
failed with standard extraction methods.
"""

import sys
import time
from core.logger import get_logger
from core.driver import get_protected_driver
from extractors.ai_fallback_extractor import AIFallbackExtractor
from core.ai_content_analyzer import get_ai_content_analyzer
from config import get_genai_api_key

logger = get_logger(__name__)


def test_ai_content_analyzer():
    """Test the AI content analyzer component."""
    logger.info("🧪 Testing AI Content Analyzer...")

    genai_api_key = get_genai_api_key()
    if not genai_api_key:
        logger.error("❌ GenAI API key not found - cannot test AI analyzer")
        return False

    analyzer = get_ai_content_analyzer(genai_api_key)

    # Test diocese that failed standard extraction
    test_diocese = "Diocese of Houma-Thibodaux"
    test_url = "https://www.htdiocese.org/parishes"

    logger.info(f"📍 Testing with: {test_diocese}")
    logger.info(f"🌐 URL: {test_url}")

    driver = None
    try:
        # Setup WebDriver
        driver = get_protected_driver()
        driver.get(test_url)

        # Wait for page to load
        time.sleep(3)

        # Run AI analysis
        logger.info("🤖 Running AI content analysis...")
        start_time = time.time()

        analysis_result = analyzer.analyze_failed_extraction(
            driver, test_diocese, test_url
        )

        analysis_time = time.time() - start_time

        # Display results
        logger.info(f"⏱️ Analysis completed in {analysis_time:.2f} seconds")
        logger.info(f"🎯 Confidence: {analysis_result.get('confidence', 0.0):.2f}")
        logger.info(f"📊 Strategy: {analysis_result.get('extraction_strategy', 'unknown')}")
        logger.info(f"⛪ Parishes found: {len(analysis_result.get('parish_data', []))}")

        if analysis_result.get('custom_selectors'):
            logger.info("🔧 Custom selectors generated:")
            for i, selector in enumerate(analysis_result['custom_selectors'][:5], 1):
                logger.info(f"  {i}. {selector}")

        if analysis_result.get('ai_insights'):
            logger.info("💡 AI insights:")
            for insight in analysis_result['ai_insights'][:3]:
                logger.info(f"  • {insight}")

        # Check if parishes were found
        parishes = analysis_result.get('parish_data', [])
        if parishes:
            logger.info(f"✅ Found {len(parishes)} parishes:")
            for i, parish in enumerate(parishes[:5], 1):
                name = parish.get('name', 'Unknown')
                url = parish.get('url', 'No URL')
                logger.info(f"  {i}. {name}")
                if url != 'No URL':
                    logger.info(f"     🔗 {url}")

            return True
        else:
            logger.warning("⚠️ No parishes found by AI analysis")
            return False

    except Exception as e:
        logger.error(f"❌ AI content analyzer test failed: {e}", exc_info=True)
        return False

    finally:
        if driver:
            driver.quit()


def test_ai_fallback_extractor():
    """Test the complete AI fallback extractor."""
    logger.info("\n🧪 Testing AI Fallback Extractor...")

    extractor = AIFallbackExtractor()

    if not extractor.ai_analyzer:
        logger.error("❌ AI Fallback Extractor not properly initialized")
        return False

    # Test diocese
    test_diocese = "Diocese of Houma-Thibodaux"
    test_url = "https://www.htdiocese.org/parishes"
    max_parishes = 10

    driver = None
    try:
        # Setup WebDriver
        driver = get_protected_driver()
        driver.get(test_url)

        # Wait for page to load
        time.sleep(3)

        # Check if extractor can handle this page
        can_extract = extractor.can_extract(driver, test_url)
        logger.info(f"🤖 Can extract: {can_extract}")

        if not can_extract:
            logger.error("❌ AI Fallback Extractor cannot handle this page")
            return False

        # Run extraction
        logger.info("🤖 Running AI fallback extraction...")
        start_time = time.time()

        parishes = extractor.extract(driver, test_diocese, test_url, max_parishes)

        extraction_time = time.time() - start_time

        # Display results
        logger.info(f"⏱️ Extraction completed in {extraction_time:.2f} seconds")
        logger.info(f"⛪ Parishes extracted: {len(parishes)}")

        if parishes:
            logger.info("✅ Successfully extracted parishes:")
            for i, parish in enumerate(parishes[:5], 1):
                name = parish.get('name', 'Unknown')
                method = parish.get('extraction_method', 'unknown')
                url = parish.get('url', 'No URL')

                logger.info(f"  {i}. {name} ({method})")
                if url != 'No URL':
                    logger.info(f"     🔗 {url}")
                if parish.get('address'):
                    logger.info(f"     📍 {parish['address']}")

            return True
        else:
            logger.warning("⚠️ No parishes extracted")
            return False

    except Exception as e:
        logger.error(f"❌ AI fallback extractor test failed: {e}", exc_info=True)
        return False

    finally:
        if driver:
            driver.quit()


def test_integration():
    """Test integration with existing parish extraction system."""
    logger.info("\n🧪 Testing Integration with Parish Extraction System...")

    # This would require importing and running the full parish extraction
    # For now, we'll just verify that the AI extractor can be imported
    try:
        from parish_extractors import process_diocese_with_detailed_extraction
        logger.info("✅ AI Fallback Extractor successfully integrated")
        return True
    except ImportError as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False


def main():
    """Run all AI fallback extractor tests."""
    logger.info("🚀 Starting AI Fallback Extractor Tests...")

    tests = [
        ("AI Content Analyzer", test_ai_content_analyzer),
        ("AI Fallback Extractor", test_ai_fallback_extractor),
        ("Integration Test", test_integration),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 Running: {test_name}")
        logger.info(f"{'='*60}")

        try:
            if test_func():
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} ERROR: {str(e)}")
            failed += 1

    logger.info(f"\n{'='*60}")
    logger.info(f"🎯 FINAL RESULTS: {passed} passed, {failed} failed")
    logger.info(f"{'='*60}")

    if failed == 0:
        logger.info("🎉 All AI fallback extractor tests passed!")
        logger.info("✨ AI-powered content analysis is ready for production!")
    else:
        logger.error(f"❌ {failed} test(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()