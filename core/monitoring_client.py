#!/usr/bin/env python3
"""
Monitoring Client for Real-time Dashboard Integration.
Provides easy integration for async extraction scripts to send updates to the monitoring dashboard.
"""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class MonitoringClient:
    """
    Client for sending monitoring updates to the dashboard backend.
    Provides easy integration for async extraction scripts.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 5  # 5 second timeout for monitoring calls
        self.enabled = True
        
        logger.info(f"🖥️ Monitoring client initialized: {base_url}")
    
    def disable(self):
        """Disable monitoring (useful for testing or standalone operation)"""
        self.enabled = False
        logger.debug("📊 Monitoring disabled")
    
    def enable(self):
        """Enable monitoring"""
        self.enabled = True
        logger.debug("📊 Monitoring enabled")
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> bool:
        """Make monitoring request with error handling"""
        if not self.enabled:
            return True
        
        try:
            url = f"{self.base_url}/api/monitoring{endpoint}"
            response = self.session.post(url, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.debug(f"Failed to send monitoring update to {endpoint}: {e}")
            return False
    
    def update_extraction_status(self, 
                               status: str,
                               current_diocese: Optional[str] = None,
                               parishes_processed: int = 0,
                               total_parishes: int = 0,
                               success_rate: float = 0.0,
                               progress_percentage: float = 0.0,
                               estimated_completion: Optional[str] = None) -> bool:
        """Update extraction status"""
        data = {
            "status": status,
            "current_diocese": current_diocese,
            "parishes_processed": parishes_processed,
            "total_parishes": total_parishes,
            "success_rate": success_rate,
            "progress_percentage": progress_percentage,
            "estimated_completion": estimated_completion,
            "started_at": datetime.now(timezone.utc).isoformat() if status == "running" else None
        }
        return self._make_request("/extraction_status", data)
    
    def update_circuit_breakers(self, circuit_breakers: Dict[str, Dict[str, Any]]) -> bool:
        """Update circuit breaker status"""
        return self._make_request("/circuit_breakers", circuit_breakers)
    
    def update_performance_metrics(self,
                                 parishes_per_minute: float = 0.0,
                                 queue_size: int = 0,
                                 pool_utilization: float = 0.0,
                                 total_requests: int = 0,
                                 successful_requests: int = 0) -> bool:
        """Update performance metrics"""
        data = {
            "parishes_per_minute": parishes_per_minute,
            "queue_size": queue_size,
            "pool_utilization": pool_utilization,
            "total_requests": total_requests,
            "successful_requests": successful_requests
        }
        return self._make_request("/performance", data)
    
    def report_error(self,
                    error_type: str,
                    message: str,
                    diocese: Optional[str] = None,
                    severity: str = "error") -> bool:
        """Report an error"""
        data = {
            "type": error_type,
            "message": message,
            "diocese": diocese,
            "severity": severity
        }
        return self._make_request("/error", data)
    
    def report_extraction_complete(self,
                                 diocese_name: str,
                                 parishes_extracted: int,
                                 success_rate: float,
                                 duration: float,
                                 status: str = "completed") -> bool:
        """Report completed extraction"""
        data = {
            "diocese_name": diocese_name,
            "parishes_extracted": parishes_extracted,
            "success_rate": success_rate,
            "duration": duration,
            "status": status
        }
        return self._make_request("/extraction_complete", data)
    
    def send_log(self,
                message: str,
                level: str = "INFO",
                module: Optional[str] = None) -> bool:
        """Send live log entry"""
        data = {
            "message": message,
            "level": level,
            "module": module or "extraction"
        }
        return self._make_request("/log", data)
    
    # Convenience methods for common scenarios
    def extraction_started(self, diocese_name: str, total_parishes: int = 0):
        """Convenience method for extraction start"""
        self.update_extraction_status(
            status="running",
            current_diocese=diocese_name,
            total_parishes=total_parishes,
            parishes_processed=0,
            progress_percentage=0.0
        )
        self.send_log(f"Started extraction for {diocese_name} ({total_parishes} parishes)", "INFO")
    
    def extraction_progress(self, 
                          diocese_name: str,
                          parishes_processed: int,
                          total_parishes: int,
                          success_rate: float):
        """Convenience method for extraction progress"""
        progress_percentage = (parishes_processed / max(total_parishes, 1)) * 100
        
        self.update_extraction_status(
            status="running",
            current_diocese=diocese_name,
            parishes_processed=parishes_processed,
            total_parishes=total_parishes,
            success_rate=success_rate,
            progress_percentage=progress_percentage
        )
        
        if parishes_processed % 5 == 0:  # Log every 5 parishes
            self.send_log(
                f"📊 Progress: {parishes_processed}/{total_parishes} parishes ({progress_percentage:.1f}%)",
                "INFO"
            )
    
    def extraction_finished(self, 
                          diocese_name: str,
                          parishes_extracted: int,
                          success_rate: float,
                          duration: float):
        """Convenience method for extraction completion"""
        self.update_extraction_status(status="idle")
        self.report_extraction_complete(
            diocese_name=diocese_name,
            parishes_extracted=parishes_extracted,
            success_rate=success_rate,
            duration=duration
        )
        self.send_log(
            f"✅ Completed {diocese_name}: {parishes_extracted} parishes, {success_rate:.1f}% success",
            "INFO"
        )
    
    def circuit_breaker_opened(self, circuit_name: str, reason: str):
        """Convenience method for circuit breaker opening"""
        self.report_error(
            error_type="CircuitBreakerOpen",
            message=f"Circuit breaker '{circuit_name}' opened: {reason}",
            severity="warning"
        )
        self.send_log(f"🚫 Circuit breaker '{circuit_name}' OPEN: {reason}", "WARNING")
    
    def circuit_breaker_closed(self, circuit_name: str):
        """Convenience method for circuit breaker recovery"""
        self.send_log(f"🟢 Circuit breaker '{circuit_name}' CLOSED - service recovered", "INFO")
    
    def performance_update(self, 
                          parishes_per_minute: float,
                          queue_size: int = 0,
                          pool_utilization: float = 0.0):
        """Convenience method for performance updates"""
        self.update_performance_metrics(
            parishes_per_minute=parishes_per_minute,
            queue_size=queue_size,
            pool_utilization=pool_utilization
        )

    def report_circuit_breaker_status(self) -> bool:
        """Report current circuit breaker status to monitoring dashboard"""
        try:
            from core.circuit_breaker import CircuitBreakerManager
            manager = CircuitBreakerManager()
            circuit_data = manager.get_all_stats()

            if circuit_data:
                # Transform the data format for the monitoring API
                monitoring_data = {}
                for name, stats in circuit_data.items():
                    monitoring_data[name] = {
                        "state": stats["state"].upper() if hasattr(stats["state"], "upper") else stats["state"],
                        "total_requests": stats["total_requests"],
                        "total_successes": stats["total_successes"],
                        "total_failures": stats["total_failures"],
                        "total_blocked": stats["total_blocked"],
                        "success_rate": float(stats["success_rate"].replace("%", "")) if isinstance(stats["success_rate"], str) else stats["success_rate"]
                    }

                return self.update_circuit_breakers(monitoring_data)
        except Exception as e:
            logger.debug(f"Failed to report circuit breaker status: {e}")
            return False
        return True


# Global monitoring client instance
_monitoring_client = None


def get_monitoring_client(base_url: str = "http://localhost:8000") -> MonitoringClient:
    """Get or create the global monitoring client instance"""
    global _monitoring_client
    
    if _monitoring_client is None:
        _monitoring_client = MonitoringClient(base_url)
    
    return _monitoring_client


def disable_monitoring():
    """Disable monitoring globally"""
    client = get_monitoring_client()
    client.disable()


def enable_monitoring():
    """Enable monitoring globally"""
    client = get_monitoring_client()
    client.enable()


# Context manager for extraction monitoring
class ExtractionMonitoring:
    """Context manager for automatic extraction monitoring"""
    
    def __init__(self, diocese_name: str, total_parishes: int = 0, base_url: str = "http://localhost:8000"):
        self.diocese_name = diocese_name
        self.total_parishes = total_parishes
        self.client = get_monitoring_client(base_url)
        self.start_time = None
        self.parishes_processed = 0
        self.successful_parishes = 0
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.client.extraction_started(self.diocese_name, self.total_parishes)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        success_rate = (self.successful_parishes / max(self.parishes_processed, 1)) * 100
        
        if exc_type is not None:
            self.client.report_error(
                error_type="ExtractionError",
                message=f"Extraction failed: {str(exc_val)}",
                diocese=self.diocese_name
            )
            status = "error"
        else:
            status = "completed"
        
        self.client.extraction_finished(
            self.diocese_name,
            self.parishes_processed,
            success_rate,
            duration
        )
    
    def update_progress(self, parishes_processed: int, successful_parishes: int):
        """Update progress during extraction"""
        self.parishes_processed = parishes_processed
        self.successful_parishes = successful_parishes
        success_rate = (successful_parishes / max(parishes_processed, 1)) * 100
        
        self.client.extraction_progress(
            self.diocese_name,
            parishes_processed,
            self.total_parishes,
            success_rate
        )