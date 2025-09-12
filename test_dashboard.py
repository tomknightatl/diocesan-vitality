#!/usr/bin/env python3
"""
Test script for the real-time monitoring dashboard.
Simulates extraction activity to demonstrate dashboard functionality.
"""

import asyncio
import time
import random
from core.monitoring_client import MonitoringClient, ExtractionMonitoring, get_monitoring_client
from core.logger import get_logger

logger = get_logger(__name__)


async def simulate_extraction_activity():
    """Simulate parish extraction activity for dashboard testing"""
    
    client = get_monitoring_client("http://localhost:8000")
    
    logger.info("🧪 Starting dashboard simulation test")
    
    # Test dioceses
    test_dioceses = [
        {"name": "Archdiocese of Atlanta", "parishes": 25},
        {"name": "Diocese of Boston", "parishes": 18},
        {"name": "Diocese of Chicago", "parishes": 32},
        {"name": "Diocese of Miami", "parishes": 15}
    ]
    
    # Simulate circuit breaker status
    circuit_breakers = {
        "diocese_page_load": {
            "state": "CLOSED",
            "total_requests": 45,
            "success_rate": "95.6%",
            "total_failures": 2,
            "total_blocked": 0
        },
        "parish_detail_load": {
            "state": "CLOSED", 
            "total_requests": 128,
            "success_rate": "87.5%",
            "total_failures": 16,
            "total_blocked": 0
        },
        "webdriver_requests": {
            "state": "HALF_OPEN",
            "total_requests": 89,
            "success_rate": "92.1%",
            "total_failures": 7,
            "total_blocked": 3
        }
    }
    
    # Send initial circuit breaker status
    client.update_circuit_breakers(circuit_breakers)
    client.send_log("🔌 Circuit breakers initialized", "INFO")
    
    # Simulate extraction for each diocese
    for diocese in test_dioceses:
        diocese_name = diocese["name"]
        total_parishes = diocese["parishes"]
        
        logger.info(f"🔄 Simulating extraction for {diocese_name}")
        
        # Use extraction monitoring context manager
        with ExtractionMonitoring(diocese_name, total_parishes) as monitor:
            try:
                parishes_processed = 0
                successful_parishes = 0
                
                # Simulate processing each parish
                for i in range(total_parishes):
                    parishes_processed += 1
                    
                    # Simulate processing time (faster for demo)
                    processing_time = random.uniform(0.2, 0.8)
                    await asyncio.sleep(processing_time)
                    
                    # Simulate success/failure (mostly successful)
                    if random.random() < 0.85:  # 85% success rate
                        successful_parishes += 1
                        if random.random() < 0.3:  # 30% chance of detailed log
                            client.send_log(
                                f"✅ Extracted parish {i+1}: Enhanced data found", 
                                "INFO"
                            )
                    else:
                        client.send_log(
                            f"⚠️ Parish {i+1}: Partial data extracted",
                            "WARNING"
                        )
                    
                    # Update progress
                    monitor.update_progress(parishes_processed, successful_parishes)
                    
                    # Update performance metrics
                    parishes_per_minute = parishes_processed / ((time.time() - monitor.start_time) / 60)
                    client.performance_update(
                        parishes_per_minute=parishes_per_minute,
                        queue_size=max(0, total_parishes - parishes_processed),
                        pool_utilization=random.uniform(60, 95)
                    )
                    
                    # Simulate occasional errors
                    if random.random() < 0.05:  # 5% chance of error
                        client.report_error(
                            error_type="ParsingError",
                            message=f"Failed to parse parish {i+1} contact information",
                            diocese=diocese_name,
                            severity="warning"
                        )
                    
                    # Simulate circuit breaker state changes
                    if random.random() < 0.02:  # 2% chance of circuit breaker event
                        if circuit_breakers["webdriver_requests"]["state"] == "CLOSED":
                            circuit_breakers["webdriver_requests"]["state"] = "HALF_OPEN"
                            client.circuit_breaker_opened("webdriver_requests", "Multiple timeouts detected")
                        elif circuit_breakers["webdriver_requests"]["state"] == "HALF_OPEN":
                            circuit_breakers["webdriver_requests"]["state"] = "CLOSED"
                            client.circuit_breaker_closed("webdriver_requests")
                        
                        client.update_circuit_breakers(circuit_breakers)
                
                # Small delay between dioceses
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in simulation: {e}")
                client.report_error(
                    error_type="SimulationError",
                    message=str(e),
                    diocese=diocese_name
                )
    
    # Final status update
    client.update_extraction_status(status="idle")
    client.send_log("🎉 Dashboard simulation test completed successfully", "INFO")
    
    logger.info("✅ Dashboard simulation completed")


async def continuous_monitoring_demo():
    """Run continuous monitoring demo with periodic updates"""
    
    client = get_monitoring_client("http://localhost:8000")
    
    logger.info("🔄 Starting continuous monitoring demo")
    client.send_log("🚀 Continuous monitoring demo started", "INFO")
    
    # Simulate ongoing system activity
    for cycle in range(10):  # Run for 10 cycles (about 5 minutes)
        try:
            # Simulate system metrics
            await asyncio.sleep(30)  # 30-second intervals
            
            # Random system activity
            activity_type = random.choice([
                "parish_validation",
                "data_cleanup",
                "schedule_extraction",
                "address_parsing"
            ])
            
            client.send_log(f"📊 Cycle {cycle + 1}: Running {activity_type}", "INFO")
            
            # Simulate performance metrics
            client.update_performance_metrics(
                parishes_per_minute=random.uniform(15, 45),
                queue_size=random.randint(0, 8),
                pool_utilization=random.uniform(20, 80)
            )
            
            # Occasional warnings
            if random.random() < 0.2:
                client.report_error(
                    error_type="SystemWarning",
                    message=f"High memory usage detected during {activity_type}",
                    severity="warning"
                )
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in continuous demo: {e}")
    
    client.send_log("🛑 Continuous monitoring demo ended", "INFO")
    logger.info("✅ Continuous monitoring demo completed")


def test_basic_monitoring():
    """Test basic monitoring functionality without async"""
    
    client = get_monitoring_client("http://localhost:8000")
    
    logger.info("🧪 Testing basic monitoring functionality")
    
    # Test all monitoring functions
    client.send_log("🔧 Testing basic monitoring functions", "INFO")
    
    # Test extraction status
    client.extraction_started("Test Diocese", 10)
    time.sleep(1)
    
    client.extraction_progress("Test Diocese", 5, 10, 90.0)
    time.sleep(1)
    
    client.extraction_finished("Test Diocese", 9, 90.0, 45.5)
    
    # Test error reporting
    client.report_error(
        error_type="TestError",
        message="This is a test error for dashboard validation",
        diocese="Test Diocese"
    )
    
    # Test performance update
    client.performance_update(
        parishes_per_minute=25.5,
        queue_size=3,
        pool_utilization=75.0
    )
    
    # Test circuit breaker updates
    test_circuits = {
        "test_circuit": {
            "state": "CLOSED",
            "total_requests": 100,
            "success_rate": "95.0%",
            "total_failures": 5,
            "total_blocked": 0
        }
    }
    client.update_circuit_breakers(test_circuits)
    
    client.send_log("✅ Basic monitoring test completed", "INFO")
    logger.info("✅ Basic monitoring test completed")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the real-time monitoring dashboard")
    parser.add_argument(
        "--mode",
        choices=["basic", "extraction", "continuous"],
        default="extraction",
        help="Test mode to run"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "basic":
            test_basic_monitoring()
        elif args.mode == "extraction":
            asyncio.run(simulate_extraction_activity())
        elif args.mode == "continuous":
            asyncio.run(continuous_monitoring_demo())
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise