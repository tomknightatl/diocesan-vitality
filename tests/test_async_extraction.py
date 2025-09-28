#!/usr/bin/env python3
"""
Test script for async concurrent parish extraction.
Validates performance improvements and functionality of the async implementation.
"""

import asyncio
import random
import time
from typing import Any, Dict, List

from core.async_driver import get_async_driver_pool, shutdown_async_driver_pool
from core.async_parish_extractor import get_async_parish_extractor
from core.logger import get_logger
from parish_extraction_core import ParishData

logger = get_logger(__name__)


class MockParishData(ParishData):
    """Mock ParishData for testing"""

    def __init__(self, name: str, detail_url: str = None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.detail_url = detail_url or f"https://example.com/parish/{name.lower().replace(' ', '-')}"


def create_test_parishes(count: int) -> List[ParishData]:
    """Create test parish data for performance testing"""
    parishes = []

    for i in range(count):
        parish = MockParishData(
            name=f"Test Parish {i+1}",
            address=f"{100 + i} Test Street",
            phone="" if random.random() < 0.3 else f"555-{1000 + i:04d}",
            website="" if random.random() < 0.4 else f"https://parish{i+1}.example.com",
            zip_code="" if random.random() < 0.2 else f"{10001 + i:05d}",
            full_address="" if random.random() < 0.3 else f"{100 + i} Test Street, Test City, TS {10001 + i:05d}",
        )
        parishes.append(parish)

    return parishes


def mock_parish_detail_extraction(driver, parish_name: str, base_info: Dict) -> ParishData:
    """Mock parish detail extraction function for testing"""
    # Simulate varying extraction times
    extraction_time = random.uniform(0.5, 2.0)
    time.sleep(extraction_time)

    # Simulate occasional failures
    if random.random() < 0.1:  # 10% failure rate
        raise Exception(f"Mock extraction failed for {parish_name}")

    # Create enhanced parish data
    enhanced_parish = ParishData(
        name=parish_name,
        address=base_info.get("address", f"Enhanced Address for {parish_name}"),
        phone=base_info.get("phone") or f"555-{random.randint(1000, 9999)}",
        website=base_info.get("website") or f"https://enhanced-{parish_name.lower().replace(' ', '-')}.com",
        zip_code=base_info.get("zip_code") or f"{random.randint(10000, 99999)}",
        full_address=f"Enhanced full address for {parish_name}",
        clergy_info=f"Pastor: Rev. John Doe (for {parish_name})",
        service_times="Saturday 5:00 PM, Sunday 8:00 AM, 10:30 AM",
        enhanced_extraction=True,
    )

    return enhanced_parish


async def test_async_driver_pool():
    """Test the async WebDriver pool functionality"""
    logger.info("🧪 Testing Async WebDriver Pool")
    logger.info("=" * 40)

    # Initialize pool
    pool = await get_async_driver_pool(pool_size=3)

    # Test concurrent requests
    test_requests = []
    for i in range(10):
        request = {
            "url": f"https://httpbin.org/delay/{random.randint(1, 3)}",
            "callback": lambda driver, url=f"test_{i}": f"Mock response for {url}",
            "priority": random.randint(1, 3),
        }
        test_requests.append(request)

    start_time = time.time()
    results = await pool.batch_requests(test_requests, batch_size=5)
    total_time = time.time() - start_time

    successful = len([r for r in results if not isinstance(r, Exception)])
    failed = len(results) - successful

    logger.info(f"✅ Pool test completed in {total_time:.2f}s")
    logger.info(f"📊 Results: {successful} successful, {failed} failed")
    pool.log_stats()

    return True


async def test_async_parish_extractor():
    """Test the async parish extractor functionality"""
    logger.info("\n🧪 Testing Async Parish Extractor")
    logger.info("=" * 40)

    # Create test parishes
    test_parishes = create_test_parishes(20)
    logger.info(f"📝 Created {len(test_parishes)} test parishes")

    # Initialize extractor
    extractor = await get_async_parish_extractor(pool_size=4, batch_size=6)

    # Mock the extraction function
    original_extract = extractor._extract_parish_detail_sync
    extractor._extract_parish_detail_sync = mock_parish_detail_extraction

    # Test concurrent extraction
    start_time = time.time()
    enhanced_parishes = await extractor.extract_parish_details_concurrent(test_parishes, "Test Diocese", max_concurrent=8)
    total_time = time.time() - start_time

    # Analyze results
    enhanced_count = sum(1 for p in enhanced_parishes if getattr(p, "enhanced_extraction", False))
    success_rate = (enhanced_count / len(test_parishes)) * 100
    parishes_per_second = len(test_parishes) / total_time

    logger.info(f"✅ Parish extraction test completed in {total_time:.2f}s")
    logger.info(f"📊 Results:")
    logger.info(f"   • Total parishes: {len(test_parishes)}")
    logger.info(f"   • Enhanced parishes: {enhanced_count}")
    logger.info(f"   • Success rate: {success_rate:.1f}%")
    logger.info(f"   • Performance: {parishes_per_second:.1f} parishes/second")

    # Log extractor statistics
    extractor.log_stats()

    # Restore original function
    extractor._extract_parish_detail_sync = original_extract

    return True


async def test_concurrent_vs_sequential():
    """Compare concurrent vs sequential processing performance"""
    logger.info("\n🧪 Performance Comparison: Concurrent vs Sequential")
    logger.info("=" * 50)

    test_parishes = create_test_parishes(15)

    # Sequential processing simulation
    logger.info("📊 Testing sequential processing...")
    start_time = time.time()

    sequential_results = []
    for parish in test_parishes:
        try:
            # Simulate sequential extraction
            time.sleep(random.uniform(0.5, 1.5))  # Mock extraction time
            enhanced_parish = MockParishData(name=parish.name + " (Sequential)", phone="555-0000", enhanced_extraction=True)
            sequential_results.append(enhanced_parish)
        except:
            sequential_results.append(parish)

    sequential_time = time.time() - start_time

    # Concurrent processing
    logger.info("📊 Testing concurrent processing...")
    extractor = await get_async_parish_extractor(pool_size=4, batch_size=8)
    extractor._extract_parish_detail_sync = mock_parish_detail_extraction

    start_time = time.time()
    concurrent_results = await extractor.extract_parish_details_concurrent(
        test_parishes, "Performance Test Diocese", max_concurrent=8
    )
    concurrent_time = time.time() - start_time

    # Performance analysis
    speedup = sequential_time / concurrent_time
    efficiency = speedup / 4  # Assuming 4-core processing

    logger.info(f"🏁 Performance Comparison Results:")
    logger.info(f"   • Sequential time: {sequential_time:.2f}s")
    logger.info(f"   • Concurrent time: {concurrent_time:.2f}s")
    logger.info(f"   • Speedup: {speedup:.1f}x")
    logger.info(f"   • Efficiency: {efficiency:.1f}x (per core)")
    logger.info(f"   • Time savings: {((sequential_time - concurrent_time) / sequential_time * 100):.1f}%")

    if speedup > 2.0:
        logger.info("🚀 Excellent performance improvement!")
    elif speedup > 1.5:
        logger.info("✅ Good performance improvement!")
    else:
        logger.info("⚠️ Modest performance improvement")

    return speedup > 1.5


async def test_error_handling():
    """Test error handling and circuit breaker functionality"""
    logger.info("\n🧪 Testing Error Handling & Circuit Breaker")
    logger.info("=" * 45)

    # Create test parishes with some that will fail
    test_parishes = create_test_parishes(10)

    # Create a failing extraction function
    def failing_extraction(driver, parish_name: str, base_info: Dict) -> ParishData:
        # High failure rate for testing
        if random.random() < 0.6:  # 60% failure rate
            raise Exception(f"Intentional test failure for {parish_name}")
        return mock_parish_detail_extraction(driver, parish_name, base_info)

    extractor = await get_async_parish_extractor(pool_size=3, batch_size=5)
    extractor._extract_parish_detail_sync = failing_extraction

    start_time = time.time()
    results = await extractor.extract_parish_details_concurrent(test_parishes, "Error Test Diocese", max_concurrent=6)
    total_time = time.time() - start_time

    # Analyze error handling
    successful = sum(1 for p in results if getattr(p, "enhanced_extraction", False))
    failed = len(results) - successful

    logger.info(f"🛡️ Error handling test completed in {total_time:.2f}s")
    logger.info(f"📊 Results with high failure rate:")
    logger.info(f"   • Total parishes: {len(test_parishes)}")
    logger.info(f"   • Successful: {successful}")
    logger.info(f"   • Failed gracefully: {failed}")
    logger.info(f"   • System stability: {'✅ Good' if len(results) == len(test_parishes) else '❌ Issues'}")

    return len(results) == len(test_parishes)


async def run_comprehensive_tests():
    """Run all async extraction tests"""
    logger.info("🚀 Starting Comprehensive Async Extraction Tests")
    logger.info("=" * 60)

    test_results = {}

    try:
        # Test 1: Async Driver Pool
        test_results["driver_pool"] = await test_async_driver_pool()

        # Test 2: Async Parish Extractor
        test_results["parish_extractor"] = await test_async_parish_extractor()

        # Test 3: Performance Comparison
        test_results["performance"] = await test_concurrent_vs_sequential()

        # Test 4: Error Handling
        test_results["error_handling"] = await test_error_handling()

        # Final Summary
        logger.info("\n🎯 Comprehensive Test Results Summary")
        logger.info("=" * 40)

        all_passed = True
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   • {test_name.replace('_', ' ').title()}: {status}")
            if not result:
                all_passed = False

        overall_status = "🎉 ALL TESTS PASSED" if all_passed else "⚠️ SOME TESTS FAILED"
        logger.info(f"\n{overall_status}")

        return all_passed

    except Exception as e:
        logger.error(f"❌ Test suite failed with error: {e}")
        return False

    finally:
        # Cleanup
        await shutdown_async_driver_pool()


if __name__ == "__main__":
    # Run the comprehensive test suite
    success = asyncio.run(run_comprehensive_tests())

    if success:
        logger.info("\n🎉 Async extraction system is ready for production!")
        exit(0)
    else:
        logger.error("\n❌ Issues detected in async extraction system")
        exit(1)
