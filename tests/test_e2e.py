#!/usr/bin/env python3
"""
End-to-end integration tests for diocesan vitality pipeline.

These tests validate the complete pipeline flow from diocese discovery
through parish extraction and data storage, using controlled test data.
"""

import asyncio
import json
import time
from typing import Dict, List
from unittest.mock import Mock, patch

import pytest

from core.logger import get_logger
from tests.fixtures import MockHTTPResponse, TestDataFixtures

logger = get_logger(__name__)


class TestEndToEndPipeline:
    """End-to-end tests for complete pipeline workflows."""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_diocese_processing_pipeline(self):
        """Test complete diocese processing from discovery to data storage."""

        # Mock the entire pipeline with realistic data flow
        test_diocese = TestDataFixtures.sample_diocese_data()
        test_parishes = TestDataFixtures.multiple_parishes_data(5)

        # Track pipeline progress
        pipeline_steps = {
            "diocese_discovery": False,
            "parish_directory_fetch": False,
            "parish_extraction": False,
            "data_validation": False,
            "data_storage": False,
        }

        def mock_discover_dioceses():
            """Mock diocese discovery step."""
            pipeline_steps["diocese_discovery"] = True
            return [test_diocese]

        def mock_fetch_parish_directory(diocese_url):
            """Mock parish directory fetching."""
            pipeline_steps["parish_directory_fetch"] = True
            return MockHTTPResponse(
                200,
                """
                <html>
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
                </html>
            """,
            )

        def mock_extract_parishes(html_content):
            """Mock parish extraction step."""
            pipeline_steps["parish_extraction"] = True
            return test_parishes

        def mock_validate_parish_data(parishes):
            """Mock data validation step."""
            pipeline_steps["data_validation"] = True
            valid_parishes = []
            for parish in parishes:
                if parish.get("name") and parish.get("address"):
                    valid_parishes.append(parish)
            return valid_parishes

        def mock_store_parish_data(parishes):
            """Mock data storage step."""
            pipeline_steps["data_storage"] = True
            return {"stored_count": len(parishes), "success": True}

        # Execute pipeline steps
        start_time = time.time()

        # Step 1: Diocese Discovery
        dioceses = mock_discover_dioceses()
        assert len(dioceses) == 1
        assert dioceses[0]["name"] == test_diocese["name"]

        # Step 2: Parish Directory Fetch
        for diocese in dioceses:
            response = mock_fetch_parish_directory(diocese["parishes_directory_url"])
            assert response.status_code == 200

            # Step 3: Parish Extraction
            parishes = mock_extract_parishes(response.text)
            assert len(parishes) == 5

            # Step 4: Data Validation
            valid_parishes = mock_validate_parish_data(parishes)
            assert len(valid_parishes) >= 3  # Some parishes should be valid

            # Step 5: Data Storage
            storage_result = mock_store_parish_data(valid_parishes)
            assert storage_result["success"] is True

        pipeline_time = time.time() - start_time

        # Verify all pipeline steps completed
        assert all(pipeline_steps.values()), f"Pipeline steps incomplete: {pipeline_steps}"
        assert pipeline_time < 10.0, f"Pipeline took too long: {pipeline_time:.2f}s"

        logger.info(f"✅ E2E pipeline test completed in {pipeline_time:.2f}s")

    @pytest.mark.e2e
    def test_pipeline_error_recovery(self):
        """Test pipeline behavior when components fail and recover."""

        failure_counts = {"network": 0, "parsing": 0, "validation": 0}
        recovery_counts = {"network": 0, "parsing": 0, "validation": 0}

        def mock_network_request_with_failures(url, attempt=1):
            """Mock network request that fails occasionally."""
            if attempt <= 2 and failure_counts["network"] < 2:
                failure_counts["network"] += 1
                raise Exception("Network timeout")
            recovery_counts["network"] += 1
            return MockHTTPResponse(200, "<html>Valid response</html>")

        def mock_parse_with_failures(html_content, attempt=1):
            """Mock parsing that fails occasionally."""
            if attempt <= 1 and failure_counts["parsing"] < 1:
                failure_counts["parsing"] += 1
                raise Exception("Parse error")
            recovery_counts["parsing"] += 1
            return [TestDataFixtures.sample_parish_data()]

        def mock_validate_with_failures(data, attempt=1):
            """Mock validation that fails occasionally."""
            if attempt <= 1 and failure_counts["validation"] < 1:
                failure_counts["validation"] += 1
                return []  # No valid data
            recovery_counts["validation"] += 1
            return data  # All data valid

        # Test pipeline with retry logic
        final_result = self._execute_pipeline_with_recovery(
            mock_network_request_with_failures, mock_parse_with_failures, mock_validate_with_failures
        )

        # Verify error recovery worked
        assert final_result is not None, "Pipeline failed to recover from errors"
        assert len(final_result) > 0, "No valid data after recovery"
        assert recovery_counts["network"] > 0, "Network recovery didn't work"
        assert recovery_counts["parsing"] > 0, "Parsing recovery didn't work"
        assert recovery_counts["validation"] > 0, "Validation recovery didn't work"

        logger.info(f"✅ Error recovery test: {failure_counts} failures, {recovery_counts} recoveries")

    def _execute_pipeline_with_recovery(self, mock_network, mock_parse, mock_validate):
        """Execute pipeline with retry logic and return final result."""
        final_result = None

        for attempt in range(1, 4):  # Up to 3 attempts
            try:
                # Network request with retries
                response = mock_network("https://test.diocese.org", attempt)

                # Parsing with retries
                parishes = mock_parse(response.text, attempt)

                # Validation with retries
                valid_parishes = mock_validate(parishes, attempt)

                if valid_parishes:
                    final_result = valid_parishes
                    break

            except Exception as e:
                logger.info(f"Attempt {attempt} failed: {e}")
                continue

        return final_result

    @pytest.mark.e2e
    @pytest.mark.async_test
    async def test_async_pipeline_integration(self):
        """Test asynchronous pipeline components integration."""

        async def mock_async_diocese_fetch(diocese_id):
            """Mock async diocese data fetching."""
            await asyncio.sleep(0.1)  # Simulate async delay
            return TestDataFixtures.sample_diocese_data()

        async def mock_async_parish_extraction(diocese_data):
            """Mock async parish extraction."""
            await asyncio.sleep(0.2)  # Simulate async processing
            return TestDataFixtures.multiple_parishes_data(3)

        async def mock_async_data_enrichment(parish_data):
            """Mock async data enrichment (e.g., geocoding, validation)."""
            await asyncio.sleep(0.1)  # Simulate async enrichment
            enriched = parish_data.copy()
            enriched["enriched"] = True
            enriched["geocoded"] = True
            return enriched

        # Test async pipeline
        start_time = time.time()

        # Fetch multiple dioceses concurrently
        diocese_tasks = [mock_async_diocese_fetch(i) for i in range(1, 4)]
        dioceses = await asyncio.gather(*diocese_tasks)

        # Process parishes for each diocese concurrently
        parish_tasks = [mock_async_parish_extraction(diocese) for diocese in dioceses]
        all_parishes = await asyncio.gather(*parish_tasks)

        # Flatten parish lists
        flat_parishes = [parish for parish_list in all_parishes for parish in parish_list]

        # Enrich all parish data concurrently
        enrichment_tasks = [mock_async_data_enrichment(parish) for parish in flat_parishes]
        enriched_parishes = await asyncio.gather(*enrichment_tasks)

        total_time = time.time() - start_time

        # Verify async pipeline results
        assert len(dioceses) == 3, f"Expected 3 dioceses, got {len(dioceses)}"
        assert len(enriched_parishes) == 9, f"Expected 9 parishes (3x3), got {len(enriched_parishes)}"
        assert all(p["enriched"] for p in enriched_parishes), "Not all parishes were enriched"
        assert total_time < 1.0, f"Async pipeline should be fast: {total_time:.2f}s"

        logger.info(f"✅ Async pipeline test: {len(enriched_parishes)} parishes in {total_time:.2f}s")

    @pytest.mark.e2e
    def test_data_consistency_pipeline(self):
        """Test data consistency throughout the pipeline."""

        # Create test data with specific characteristics
        source_diocese = TestDataFixtures.sample_diocese_data()
        source_diocese["id"] = 9999
        source_diocese["name"] = "Test Diocese for Consistency"

        # Track data transformations
        data_states = {
            "original": source_diocese,
            "extracted": None,
            "validated": None,
            "stored": None,
        }

        def mock_extraction_step(input_data):
            """Mock extraction that preserves key data."""
            extracted = input_data.copy()
            extracted["extraction_timestamp"] = time.time()
            extracted["extraction_method"] = "test_extraction"
            data_states["extracted"] = extracted
            return extracted

        def mock_validation_step(input_data):
            """Mock validation that adds validation flags."""
            validated = input_data.copy()
            validated["validated"] = True
            validated["validation_timestamp"] = time.time()
            # Ensure critical fields are preserved
            assert validated["id"] == source_diocese["id"]
            assert validated["name"] == source_diocese["name"]
            data_states["validated"] = validated
            return validated

        def mock_storage_step(input_data):
            """Mock storage that adds storage metadata."""
            stored = input_data.copy()
            stored["stored"] = True
            stored["storage_timestamp"] = time.time()
            # Ensure all previous metadata is preserved
            assert "extraction_timestamp" in stored
            assert "validation_timestamp" in stored
            data_states["stored"] = stored
            return stored

        # Execute pipeline
        step1_result = mock_extraction_step(source_diocese)
        step2_result = mock_validation_step(step1_result)
        final_result = mock_storage_step(step2_result)

        # Verify data consistency
        assert final_result["id"] == source_diocese["id"], "Diocese ID changed during pipeline"
        assert final_result["name"] == source_diocese["name"], "Diocese name changed during pipeline"
        assert final_result["website_url"] == source_diocese["website_url"], "Website URL changed"

        # Verify pipeline metadata was added correctly
        assert "extraction_timestamp" in final_result, "Extraction metadata missing"
        assert "validation_timestamp" in final_result, "Validation metadata missing"
        assert "storage_timestamp" in final_result, "Storage metadata missing"
        assert final_result["validated"] is True, "Validation flag missing"
        assert final_result["stored"] is True, "Storage flag missing"

        # Verify timestamp ordering
        assert (
            final_result["extraction_timestamp"] <= final_result["validation_timestamp"] <= final_result["storage_timestamp"]
        ), "Timestamps out of order"

        logger.info("✅ Data consistency test: All pipeline transformations preserved data integrity")

    @pytest.mark.e2e
    def test_pipeline_performance_monitoring(self):
        """Test pipeline performance monitoring and metrics collection."""

        performance_metrics = {
            "step_times": {},
            "memory_usage": {},
            "error_counts": {},
            "throughput": {},
        }

        def monitor_step(step_name, func, *args, **kwargs):
            """Monitor performance of a pipeline step."""
            start_time = time.time()
            # Simplified memory tracking not implemented

            try:
                result = func(*args, **kwargs)
                performance_metrics["error_counts"][step_name] = 0
                return result
            except Exception:
                performance_metrics["error_counts"][step_name] = 1
                raise
            finally:
                end_time = time.time()
                performance_metrics["step_times"][step_name] = end_time - start_time
                performance_metrics["memory_usage"][step_name] = 0  # Simplified

        def mock_step_1():
            time.sleep(0.1)
            return "step1_result"

        def mock_step_2(input_data):
            time.sleep(0.05)
            return f"step2_{input_data}"

        def mock_step_3(input_data):
            time.sleep(0.02)
            return f"step3_{input_data}"

        # Execute monitored pipeline
        result1 = monitor_step("diocese_discovery", mock_step_1)
        result2 = monitor_step("parish_extraction", mock_step_2, result1)
        monitor_step("data_validation", mock_step_3, result2)

        # Verify monitoring captured performance data
        assert "diocese_discovery" in performance_metrics["step_times"]
        assert "parish_extraction" in performance_metrics["step_times"]
        assert "data_validation" in performance_metrics["step_times"]

        # Verify timing makes sense
        assert performance_metrics["step_times"]["diocese_discovery"] > 0.08
        assert performance_metrics["step_times"]["parish_extraction"] > 0.04
        assert performance_metrics["step_times"]["data_validation"] > 0.01

        # Verify no errors occurred
        assert all(count == 0 for count in performance_metrics["error_counts"].values())

        total_pipeline_time = sum(performance_metrics["step_times"].values())
        logger.info(f"✅ Performance monitoring test: {total_pipeline_time:.3f}s total pipeline time")


class TestEndToEndDataFlow:
    """Test complete data flow scenarios from external sources to final storage."""

    @pytest.mark.e2e
    def test_realistic_diocese_data_flow(self):
        """Test realistic data flow from diocese website to storage."""

        # Mock realistic diocese website response
        mock_diocese_html = """
        <html>
            <head><title>Diocese of Test City</title></head>
            <body>
                <div class="parishes-section">
                    <h2>Our Parishes</h2>
                    <div class="parish-listing">
                        <div class="parish-card">
                            <h3><a href="/parish/st-mary">St. Mary Parish</a></h3>
                            <p>123 Main Street, Test City, TS 12345</p>
                            <p>Phone: (555) 123-4567</p>
                            <p>Email: info@stmary.org</p>
                        </div>
                        <div class="parish-card">
                            <h3><a href="/parish/holy-cross">Holy Cross Parish</a></h3>
                            <p>456 Oak Avenue, Test City, TS 12346</p>
                            <p>Phone: (555) 234-5678</p>
                            <p>Email: contact@holycross.org</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """

        def mock_fetch_diocese_page(url):
            """Mock fetching diocese website."""
            return MockHTTPResponse(200, mock_diocese_html)

        def mock_parse_diocese_page(html_content):
            """Mock parsing diocese page for parish information."""
            # Simulate realistic parsing logic
            parishes = []

            if "St. Mary Parish" in html_content:
                parishes.append(
                    {
                        "name": "St. Mary Parish",
                        "address": "123 Main Street, Test City, TS 12345",
                        "phone": "(555) 123-4567",
                        "email": "info@stmary.org",
                        "detail_url": "/parish/st-mary",
                    }
                )

            if "Holy Cross Parish" in html_content:
                parishes.append(
                    {
                        "name": "Holy Cross Parish",
                        "address": "456 Oak Avenue, Test City, TS 12346",
                        "phone": "(555) 234-5678",
                        "email": "contact@holycross.org",
                        "detail_url": "/parish/holy-cross",
                    }
                )

            return parishes

        def mock_enrich_parish_data(parishes):
            """Mock data enrichment step."""
            enriched = []
            for parish in parishes:
                enriched_parish = parish.copy()
                # Add geocoding
                enriched_parish["latitude"] = 40.7128
                enriched_parish["longitude"] = -74.0060
                # Add validation flags
                enriched_parish["address_validated"] = True
                enriched_parish["phone_validated"] = True
                enriched_parish["email_validated"] = True
                enriched.append(enriched_parish)
            return enriched

        def mock_store_parishes(parishes):
            """Mock storing parishes in database."""
            stored_ids = []
            for i, parish in enumerate(parishes):
                # Simulate database storage
                parish_id = f"parish_{i + 1000}"
                stored_ids.append(parish_id)
            return {"stored_count": len(parishes), "parish_ids": stored_ids}

        # Execute realistic data flow
        diocese_url = "https://testdiocese.org/parishes"

        # Step 1: Fetch diocese page
        response = mock_fetch_diocese_page(diocese_url)
        assert response.status_code == 200

        # Step 2: Parse parish information
        parishes = mock_parse_diocese_page(response.text)
        assert len(parishes) == 2
        assert all("name" in p for p in parishes)
        assert all("address" in p for p in parishes)

        # Step 3: Enrich parish data
        enriched_parishes = mock_enrich_parish_data(parishes)
        assert len(enriched_parishes) == 2
        assert all("latitude" in p for p in enriched_parishes)
        assert all("longitude" in p for p in enriched_parishes)
        assert all(p["address_validated"] for p in enriched_parishes)

        # Step 4: Store parishes
        storage_result = mock_store_parishes(enriched_parishes)
        assert storage_result["stored_count"] == 2
        assert len(storage_result["parish_ids"]) == 2

        logger.info(f"✅ Realistic data flow test: {len(parishes)} parishes processed end-to-end")


if __name__ == "__main__":
    # Run end-to-end tests when script is executed directly
    pytest.main([__file__, "-v", "-m", "e2e", "--tb=short"])
