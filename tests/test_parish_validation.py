#!/usr/bin/env python3
"""
Test script specifically for parish validation system.
Tests the ability to distinguish between actual parishes and diocesan departments.
"""

import sys

from core.logger import get_logger
from core.parish_validation import filter_valid_parishes, parish_validator, validate_parish_entity

logger = get_logger(__name__)


def test_parish_validation_examples():
    """Test validation with realistic examples from Diocese extraction."""
    logger.info("🔍 Testing parish validation with realistic examples...")

    # Test cases based on actual diocesan website extraction
    test_cases = [
        # Valid parishes (should PASS validation)
        {"name": "St. Mary's Catholic Church", "expected": True},
        {"name": "Holy Trinity Parish", "expected": True},
        {"name": "Sacred Heart Cathedral", "expected": True},
        {"name": "Our Lady of Perpetual Help Church", "expected": True},
        {"name": "Saint Joseph Catholic Church", "expected": True},
        {"name": "Assumption of the Blessed Virgin Mary", "expected": True},
        {"name": "Christ the King Catholic Church", "expected": True},
        {"name": "St. Patrick's Parish", "expected": True},
        # Diocesan departments (should FAIL validation)
        {"name": "Office of the Chancellor", "expected": False},
        {"name": "Department of Religious Education", "expected": False},
        {"name": "Catholic Charities Office", "expected": False},
        {"name": "Diocesan Finance Council", "expected": False},
        {"name": "Marriage Tribunal", "expected": False},
        {"name": "Youth Ministry Director", "expected": False},
        {"name": "Office of Communications", "expected": False},
        {"name": "Vocations Office", "expected": False},
        {"name": "Human Resources Department", "expected": False},
        {"name": "Bishop's Office", "expected": False},
        {"name": "Diocesan Schools Office", "expected": False},
        {"name": "Development Office", "expected": False},
        # Edge cases
        {"name": "Catholic School", "expected": False},  # School, not parish
        {
            "name": "St. Mary's Meeting Rooms",
            "expected": False,
        },  # Facilities, not parish
        {"name": "Holy Family Retreat Center", "expected": False},  # Retreat center
        {"name": "St. Joseph Community", "expected": True},  # Community = parish
        {"name": "HOME", "expected": False},  # Navigation link
        {"name": "Contact Us", "expected": False},  # Navigation link
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        name = test["name"]
        expected = test["expected"]

        result = validate_parish_entity(name)
        status = "✅" if result == expected else "❌"

        if result == expected:
            passed += 1
        else:
            failed += 1

        logger.info(f"  {status} '{name}' -> {result} (expected {expected})")

    logger.info(f"\n📊 Validation Test Results: {passed} passed, {failed} failed")
    assert failed == 0, f"Validation test failed: {failed} tests failed"
    return True


def test_batch_filtering():
    """Test batch filtering functionality."""
    logger.info("\n🔄 Testing batch parish filtering...")

    # Sample extraction results that might come from a diocese
    sample_entities = [
        {"name": "St. Mary's Catholic Church", "url": "https://stmarys.org"},
        {"name": "Office of the Chancellor", "url": "https://diocese.org/chancellor"},
        {"name": "Holy Trinity Parish", "address": "123 Main St, Anytown"},
        {"name": "Department of Religious Education"},
        {
            "name": "Sacred Heart Cathedral",
            "url": "https://sacredheart.org",
            "address": "456 Oak Ave",
        },
        {"name": "Catholic Charities Office", "url": "https://diocese.org/charities"},
        {"name": "St. Joseph Catholic Church"},
        {"name": "Marriage Tribunal"},
        {"name": "Our Lady of Grace Parish", "address": "789 Pine St"},
        {"name": "Youth Ministry Director"},
    ]

    logger.info(f"Input: {len(sample_entities)} extracted entities")

    # Apply filtering
    valid_parishes = filter_valid_parishes(sample_entities)

    logger.info(f"Output: {len(valid_parishes)} validated parishes")

    # Show results
    logger.info("✅ Validated Parishes:")
    for parish in valid_parishes:
        validation_info = parish.get("validation", {})
        confidence = validation_info.get("confidence", 0.0)
        logger.info(f"  • {parish['name']} (confidence: {confidence:.2f})")

    logger.info(
        f"\n📈 Filtering efficiency: {len(valid_parishes)}/{len(sample_entities)} = {len(valid_parishes)/len(sample_entities)*100:.1f}% parishes retained"
    )

    assert len(valid_parishes) == 5, f"Expected 5 parishes, got {len(valid_parishes)}"  # Should retain 5 actual parishes
    return True


def test_validation_statistics():
    """Test validation statistics functionality."""
    logger.info("\n📊 Testing validation statistics...")

    sample_entities = [
        {"name": "St. Mary's Catholic Church"},
        {"name": "Office of the Chancellor"},
        {"name": "Holy Trinity Parish"},
        {"name": "Department of Religious Education"},
        {"name": "Sacred Heart Cathedral"},
        {"name": "Catholic Charities Office"},
        {"name": "St. Joseph Catholic Church"},
        {"name": "Marriage Tribunal"},
        {"name": "Our Lady of Grace Parish"},
        {"name": "Youth Ministry Director"},
    ]

    stats = parish_validator.get_validation_stats(sample_entities)

    logger.info("📋 Validation Statistics:")
    logger.info(f"  Total entities: {stats['total']}")
    logger.info(f"  Valid parishes: {stats['valid_parishes']}")
    logger.info(f"  Excluded admin: {stats['excluded_admin']}")
    logger.info(f"  High confidence: {stats['high_confidence']}")
    logger.info(f"  Low confidence: {stats['low_confidence']}")

    if stats["parish_indicators"]:
        logger.info("  Top parish indicators:")
        for indicator, count in list(stats["parish_indicators"].items())[:3]:
            logger.info(f"    • {indicator}: {count}")

    if stats["exclusion_reasons"]:
        logger.info("  Top exclusion reasons:")
        for reason, count in list(stats["exclusion_reasons"].items())[:3]:
            logger.info(f"    • {reason}: {count}")

    assert (
        stats["valid_parishes"] == 5 and stats["excluded_admin"] == 5
    ), f"Expected 5 valid parishes and 5 excluded admin, got {stats['valid_parishes']} valid and {stats['excluded_admin']} excluded"
    return True


def main():
    """Run all parish validation tests."""
    logger.info("🚀 Starting parish validation system tests...")

    tests = [
        ("Parish Validation Examples", test_parish_validation_examples),
        ("Batch Filtering", test_batch_filtering),
        ("Validation Statistics", test_validation_statistics),
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
        logger.info("🎉 All parish validation tests passed!")
        logger.info("\n✨ Parish validation system is ready to filter diocesan departments!")
    else:
        logger.error(f"❌ {failed} test(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
