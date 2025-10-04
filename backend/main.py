import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketState

from supabase import Client, create_client

# Load .env file from the project root
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
supabase: Client = create_client(supabase_url, supabase_key)


# Global monitoring state
class MonitoringManager:
    def __init__(self):
        self.websocket_connections: Set[WebSocket] = set()
        self.start_time = time.time()

        # Dead man's switch configuration
        self.extraction_timeout = 300  # 5 minutes without updates = stale
        self.circuit_breaker_timeout = 600  # 10 minutes without updates = stale

        # Multi-worker support: worker_id -> worker_data
        self.workers = {}  # worker_id -> worker monitoring data
        self.aggregate_mode = True  # Default to aggregate view

        # Legacy single-worker data (for backward compatibility)
        self.extraction_status = {
            "status": "idle",
            "current_diocese": None,
            "parishes_processed": 0,
            "total_parishes": 0,
            "success_rate": 0,
            "started_at": None,
            "progress_percentage": 0,
            "estimated_completion": None,
        }
        self.extraction_last_updated = time.time()

        self.circuit_breakers = {}
        self.circuit_breakers_last_updated = time.time()

        self.performance_metrics = {
            "parishes_per_minute": 0,
            "queue_size": 0,
            "pool_utilization": 0,
            "total_requests": 0,
            "successful_requests": 0,
        }
        self.recent_errors = []
        self.extraction_history = []
        self.max_errors = 50

    async def add_connection(self, websocket: WebSocket):
        """Add a new WebSocket connection"""
        self.websocket_connections.add(websocket)
        print(f"New WebSocket connection added. Total: {len(self.websocket_connections)}")

        # Send initial state to new connection
        await self.send_to_connection(websocket, {"type": "system_health", "payload": self.get_system_health()})
        await self.send_to_connection(websocket, {"type": "extraction_status", "payload": self.extraction_status})
        await self.send_to_connection(websocket, {"type": "circuit_breaker_status", "payload": self.circuit_breakers})
        await self.send_to_connection(websocket, {"type": "performance_metrics", "payload": self.performance_metrics})

    async def remove_connection(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.websocket_connections.discard(websocket)
        print(f"WebSocket connection removed. Total: {len(self.websocket_connections)}")

    async def send_to_connection(self, websocket: WebSocket, message: Dict):
        """Send message to a specific WebSocket connection"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Error sending message to WebSocket: {e}")
            await self.remove_connection(websocket)

    async def broadcast(self, message: Dict):
        """Broadcast message to all connected WebSocket clients"""
        if not self.websocket_connections:
            return

        disconnected = set()
        for websocket in self.websocket_connections.copy():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message))
                else:
                    disconnected.add(websocket)
            except Exception as e:
                print(f"Error broadcasting to WebSocket: {e}")
                disconnected.add(websocket)

        # Remove disconnected connections
        for ws in disconnected:
            await self.remove_connection(ws)

    def get_system_health(self):
        """Get current system health metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            uptime = time.time() - self.start_time

            status = "healthy"
            if cpu_percent > 80 or memory.percent > 85:
                status = "warning"

            return {
                "status": status,
                "cpu_usage": round(cpu_percent, 1),
                "memory_usage": round(memory.percent, 1),
                "uptime": round(uptime),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    async def update_extraction_status(self, status_data: Dict):
        """Update and broadcast extraction status"""
        self.extraction_status.update(status_data)
        self.extraction_last_updated = time.time()  # Update timestamp
        await self.broadcast({"type": "extraction_status", "payload": self.extraction_status})

    async def update_circuit_breakers(self, circuit_data: Dict):
        """Update and broadcast circuit breaker status"""
        self.circuit_breakers.update(circuit_data)
        self.circuit_breakers_last_updated = time.time()  # Update timestamp
        await self.broadcast({"type": "circuit_breaker_status", "payload": self.circuit_breakers})

    async def update_performance_metrics(self, metrics_data: Dict):
        """Update and broadcast performance metrics"""
        self.performance_metrics.update(metrics_data)
        await self.broadcast({"type": "performance_metrics", "payload": self.performance_metrics})

    async def add_error(self, error_data: Dict):
        """Add error to recent errors and broadcast"""
        error_entry = {**error_data, "timestamp": datetime.now(timezone.utc).isoformat()}
        self.recent_errors.insert(0, error_entry)
        self.recent_errors = self.recent_errors[: self.max_errors]

        await self.broadcast({"type": "error_alert", "payload": error_entry})

    async def add_extraction_complete(self, extraction_data: Dict):
        """Add completed extraction to history"""
        extraction_entry = {**extraction_data, "timestamp": datetime.now(timezone.utc).isoformat()}
        self.extraction_history.insert(0, extraction_entry)
        self.extraction_history = self.extraction_history[:20]  # Keep last 20

        await self.broadcast({"type": "extraction_complete", "payload": extraction_entry})

    async def send_live_log(self, log_data: Dict):
        """Send live log entry to all connections"""
        log_entry = {**log_data, "timestamp": datetime.now(timezone.utc).isoformat()}
        await self.broadcast({"type": "live_log", "payload": log_entry})

    def check_and_reset_stale_data(self):
        """Check for stale data and reset to safe defaults"""
        current_time = time.time()
        changes_made = False

        # Check extraction status staleness
        if (
            self.extraction_status["status"] in ["running", "paused"]
            and current_time - self.extraction_last_updated > self.extraction_timeout
        ):

            print(
                f"⚠️ Extraction status is stale (last updated {current_time - self.extraction_last_updated:.0f}s ago), resetting to stale"
            )
            self.extraction_status = {
                "status": "stale",
                "current_diocese": None,
                "parishes_processed": 0,
                "total_parishes": 0,
                "success_rate": 0,
                "started_at": None,
                "progress_percentage": 0,
                "estimated_completion": None,
                "stale_reason": f"No updates for {(current_time - self.extraction_last_updated)/60:.1f} minutes",
            }
            self.extraction_last_updated = current_time
            changes_made = True

        # Check circuit breaker staleness
        if self.circuit_breakers and current_time - self.circuit_breakers_last_updated > self.circuit_breaker_timeout:

            print(
                f"⚠️ Circuit breaker data is stale (last updated {current_time - self.circuit_breakers_last_updated:.0f}s ago), clearing"
            )
            self.circuit_breakers = {}
            self.circuit_breakers_last_updated = current_time
            changes_made = True

        return changes_made

    async def get_current_extraction_status(self):
        """Get extraction status with staleness check"""
        self.check_and_reset_stale_data()
        return self.extraction_status

    async def get_current_circuit_breakers(self):
        """Get circuit breakers with staleness check"""
        self.check_and_reset_stale_data()
        return self.circuit_breakers

    # Multi-worker support methods
    def init_worker(self, worker_id: str):
        """Initialize a new worker in the monitoring system"""
        if worker_id not in self.workers:
            self.workers[worker_id] = {
                "worker_id": worker_id,
                "extraction_status": {
                    "status": "idle",
                    "current_diocese": None,
                    "parishes_processed": 0,
                    "total_parishes": 0,
                    "success_rate": 0,
                    "started_at": None,
                    "progress_percentage": 0,
                    "estimated_completion": None,
                },
                "circuit_breakers": {},
                "performance_metrics": {
                    "parishes_per_minute": 0,
                    "queue_size": 0,
                    "pool_utilization": 0,
                    "total_requests": 0,
                    "successful_requests": 0,
                },
                "last_updated": time.time(),
                "recent_errors": [],
                "extraction_history": [],
            }
            print(f"📊 Initialized monitoring for worker: {worker_id}")

    async def update_worker_extraction_status(self, worker_id: str, status_data: Dict):
        """Update extraction status for a specific worker"""
        self.init_worker(worker_id)
        self.workers[worker_id]["extraction_status"].update(status_data)
        self.workers[worker_id]["last_updated"] = time.time()

        # Also update legacy data for backward compatibility with single worker
        if not self.aggregate_mode:
            self.extraction_status.update(status_data)
            self.extraction_last_updated = time.time()

        # Broadcast worker-specific update
        await self.broadcast(
            {
                "type": "worker_extraction_status",
                "payload": {"worker_id": worker_id, "status": self.workers[worker_id]["extraction_status"]},
            }
        )

        # If in aggregate mode, also broadcast aggregate data
        if self.aggregate_mode:
            aggregate_status = self.get_aggregate_extraction_status()
            await self.broadcast({"type": "extraction_status", "payload": aggregate_status})

    async def update_worker_circuit_breakers(self, worker_id: str, circuit_data: Dict):
        """Update circuit breaker status for a specific worker"""
        self.init_worker(worker_id)
        self.workers[worker_id]["circuit_breakers"].update(circuit_data)
        self.workers[worker_id]["last_updated"] = time.time()

        # Broadcast aggregate circuit breaker data
        aggregate_circuits = self.get_aggregate_circuit_breakers()
        await self.broadcast({"type": "circuit_breaker_status", "payload": aggregate_circuits})

    def get_aggregate_extraction_status(self):
        """Calculate aggregate extraction status across all workers"""
        if not self.workers:
            return self.extraction_status

        active_workers = [w for w in self.workers.values() if w["extraction_status"]["status"] in ["running", "paused"]]

        if not active_workers:
            return {
                "status": "idle",
                "current_diocese": None,
                "parishes_processed": 0,
                "total_parishes": 0,
                "success_rate": 0,
                "started_at": None,
                "progress_percentage": 0,
                "estimated_completion": None,
                "active_workers": len([w for w in self.workers.values() if w["extraction_status"]["status"] != "idle"]),
            }

        # Aggregate data from active workers
        total_parishes_processed = sum(w["extraction_status"]["parishes_processed"] for w in active_workers)
        total_parishes = sum(w["extraction_status"]["total_parishes"] for w in active_workers)

        # Calculate weighted success rate
        success_rates = [
            w["extraction_status"]["success_rate"] for w in active_workers if w["extraction_status"]["parishes_processed"] > 0
        ]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0

        # Get earliest start time
        start_times = [w["extraction_status"]["started_at"] for w in active_workers if w["extraction_status"]["started_at"]]
        earliest_start = min(start_times) if start_times else None

        # Get current dioceses being processed
        current_dioceses = [
            w["extraction_status"]["current_diocese"] for w in active_workers if w["extraction_status"]["current_diocese"]
        ]

        return {
            "status": "running" if active_workers else "idle",
            "current_diocese": ", ".join(current_dioceses) if current_dioceses else None,
            "parishes_processed": total_parishes_processed,
            "total_parishes": total_parishes,
            "success_rate": round(avg_success_rate, 1),
            "started_at": earliest_start,
            "progress_percentage": (total_parishes_processed / max(total_parishes, 1)) * 100 if total_parishes > 0 else 0,
            "estimated_completion": None,  # Could be calculated based on processing rate
            "active_workers": len(active_workers),
            "total_workers": len(self.workers),
        }

    def get_aggregate_circuit_breakers(self):
        """Aggregate circuit breaker data across all workers"""
        if not self.workers:
            return self.circuit_breakers

        aggregate_circuits = {}

        # Collect all unique circuit breaker names
        all_circuit_names = set()
        for worker in self.workers.values():
            all_circuit_names.update(worker["circuit_breakers"].keys())

        # Aggregate data for each circuit breaker
        for circuit_name in all_circuit_names:
            total_requests = 0
            total_successes = 0
            total_failures = 0
            total_blocked = 0
            states = []

            for worker in self.workers.values():
                if circuit_name in worker["circuit_breakers"]:
                    cb = worker["circuit_breakers"][circuit_name]
                    total_requests += cb.get("total_requests", 0)
                    total_successes += cb.get("total_successes", 0)
                    total_failures += cb.get("total_failures", 0)
                    total_blocked += cb.get("total_blocked", 0)
                    states.append(cb.get("state", "CLOSED"))

            # Determine aggregate state (worst state wins)
            if "OPEN" in states:
                aggregate_state = "OPEN"
            elif "HALF_OPEN" in states:
                aggregate_state = "HALF_OPEN"
            else:
                aggregate_state = "CLOSED"

            # Calculate success rate
            success_rate = (total_successes / max(total_requests, 1)) * 100 if total_requests > 0 else 0

            aggregate_circuits[circuit_name] = {
                "state": aggregate_state,
                "total_requests": total_requests,
                "total_successes": total_successes,
                "total_failures": total_failures,
                "total_blocked": total_blocked,
                "success_rate": round(success_rate, 1),
            }

        return aggregate_circuits

    def get_worker_list(self):
        """Get list of all workers with their basic status, classified by activity"""
        try:
            # Query database for active workers from pipeline_workers table
            response = supabase.table("pipeline_workers").select("*").execute()

            if not response.data:
                return []

            current_time = time.time()
            worker_list = []

            for worker in response.data:
                # Parse last_heartbeat timestamp
                last_heartbeat = worker.get("last_heartbeat")
                if last_heartbeat:
                    # Convert ISO timestamp to epoch time
                    from datetime import datetime
                    heartbeat_dt = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                    last_updated = heartbeat_dt.timestamp()
                else:
                    last_updated = 0

                time_since_update = current_time - last_updated

                # Classify worker status based on last heartbeat time
                if time_since_update <= 60:  # Active: heartbeat within 1 minute
                    worker_status = "active"
                elif time_since_update <= 300:  # Recent: heartbeat within 5 minutes
                    worker_status = "recent"
                else:  # Stale: no heartbeat for more than 5 minutes
                    worker_status = "stale"

                worker_list.append({
                    "worker_id": worker.get("worker_id", "unknown"),
                    "status": worker.get("status", "unknown"),
                    "worker_status": worker_status,
                    "current_diocese": worker.get("current_diocese"),
                    "parishes_processed": worker.get("parishes_processed", 0),
                    "last_updated": last_updated,
                    "time_since_update": int(time_since_update),
                })

            # Sort by activity: active first, then recent, then stale
            worker_list.sort(
                key=lambda w: (
                    0 if w["worker_status"] == "active" else 1 if w["worker_status"] == "recent" else 2,
                    -w["last_updated"],
                )
            )

            return worker_list

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Error fetching worker list from database: {e}", file=sys.stderr)
            print(f"Error details: {error_details}", file=sys.stderr)
            # Fallback to empty list if database query fails
            return []


# Global monitoring manager instance
monitoring_manager = MonitoringManager()


# Background task to periodically update system health
async def periodic_health_update():
    """Periodically broadcast system health updates and check for stale data"""
    while True:
        try:
            # Check for stale data and reset if needed
            changes_made = monitoring_manager.check_and_reset_stale_data()

            # Broadcast system health
            health_data = monitoring_manager.get_system_health()
            await monitoring_manager.broadcast({"type": "system_health", "payload": health_data})

            # If stale data was detected and reset, broadcast the updates
            if changes_made:
                await monitoring_manager.broadcast(
                    {"type": "extraction_status", "payload": monitoring_manager.extraction_status}
                )
                await monitoring_manager.broadcast(
                    {"type": "circuit_breaker_status", "payload": monitoring_manager.circuit_breakers}
                )

            await asyncio.sleep(10)  # Update every 10 seconds
        except Exception as e:
            print(f"Error in periodic health update: {e}")
            await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    asyncio.create_task(periodic_health_update())
    print("🖥️ Real-time monitoring dashboard backend started")
    print(f"📊 WebSocket monitoring available at: /ws/monitoring")
    print(f"🔧 API monitoring endpoints available at: /api/monitoring/*")

    yield

    # Shutdown (if needed)
    print("🛑 Shutting down monitoring dashboard backend")


app = FastAPI(lifespan=lifespan)

# Configure CORS middleware
origins = [
    "http://diocesanvitality.org",
    "https://diocesanvitality.org",
    "http://diocesanvitality.org",
    "https://diocesanvitality.org",
    "http://localhost:3000",  # React development server
    "http://localhost:8080",
    "http://localhost:8081",
    "http://localhost:5173",  # Vite development server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Check if credentials are set
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials not found in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.get("/api")
def read_root():
    return {"message": "Hello from the Python backend!"}


@app.get("/api/summary")
async def get_summary():
    """
    Provides a summary of dioceses and their parish directory URLs.
    """
    try:
        # Dioceses summary
        total_dioceses_response = supabase.table("Dioceses").select("count", count="exact").execute()
        total_dioceses_processed = total_dioceses_response.count

        dir_response = supabase.table("DiocesesParishDirectory").select("diocese_id").execute()
        dir_data = dir_response.data
        dioceses_with_parish_directories_found = len(set(item["diocese_id"] for item in dir_data))
        dioceses_without_parish_directories_found = total_dioceses_processed - dioceses_with_parish_directories_found

        # Parishes summary
        parishes_count_response = supabase.table("Parishes").select("count", count="exact").execute()
        parishes_extracted = parishes_count_response.count

        parish_data_response = supabase.table("ParishData").select("parish_id, fact_value").execute()
        parish_data = parish_data_response.data

        parishes_with_data_extracted = len(
            set(
                item["parish_id"]
                for item in parish_data
                if item["fact_value"] and item["fact_value"] != "Information not found"
            )
        )

        parishes_with_data_not_extracted = parishes_extracted - parishes_with_data_extracted

        return {
            "total_dioceses_processed": total_dioceses_processed,
            "found_parish_directories": dioceses_with_parish_directories_found,
            "not_found_parish_directories": dioceses_without_parish_directories_found,
            "parishes_extracted": parishes_extracted,
            "parishes_with_data_extracted": parishes_with_data_extracted,
            "parishes_with_data_not_extracted": parishes_with_data_not_extracted,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/dioceses")
def get_dioceses(
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "Name",
    sort_order: str = "asc",
    filter_name: str = None,
    filter_address: str = None,
    filter_website: str = None,
):
    """
    Fetches records from the 'Dioceses' table with pagination, sorting, and filtering.
    """
    try:
        offset = (page - 1) * page_size

        query = supabase.table("Dioceses").select("*")
        dioceses = query.execute().data

        # Apply filtering in Python
        if filter_name:
            dioceses = [d for d in dioceses if filter_name.lower() in d.get("Name", "").lower()]
        if filter_address:
            dioceses = [d for d in dioceses if filter_address.lower() in d.get("Address", "").lower()]
        if filter_website:
            dioceses = [d for d in dioceses if filter_website.lower() in d.get("Website", "").lower()]

        total_count = len(dioceses)

        # Fetch additional data including blocking detection
        all_dir_response = (
            supabase.table("DiocesesParishDirectory")
            .select(
                "diocese_id, parish_directory_url, is_blocked, blocking_type, blocking_evidence, status_code, robots_txt_check, respectful_automation_used, status_description"
            )
            .execute()
        )
        dir_url_map = {item["diocese_id"]: item["parish_directory_url"] for item in all_dir_response.data}
        blocking_data_map = {
            item["diocese_id"]: {
                "is_blocked": item.get("is_blocked", False),
                "blocking_type": item.get("blocking_type"),
                "blocking_evidence": item.get("blocking_evidence", {}),
                "status_code": item.get("status_code"),
                "robots_txt_check": item.get("robots_txt_check", {}),
                "respectful_automation_used": item.get("respectful_automation_used", False),
                "status_description": item.get("status_description", "Unknown"),
            }
            for item in all_dir_response.data
        }

        parishes_response = supabase.table("Parishes").select("id, diocese_url").execute()
        parishes_map = {p["id"]: p["diocese_url"] for p in parishes_response.data}
        parish_counts = {}
        for parish in parishes_response.data:
            url = parish["diocese_url"]
            parish_counts[url] = parish_counts.get(url, 0) + 1

        parish_data_response = supabase.table("ParishData").select("parish_id, fact_value").execute()
        parishes_with_data = {
            item["parish_id"]
            for item in parish_data_response.data
            if item["fact_value"] and item["fact_value"] != "Information not found"
        }

        parishes_with_data_extracted_counts = {}
        for parish_id in parishes_with_data:
            if parish_id in parishes_map:
                diocese_url = parishes_map[parish_id]
                parishes_with_data_extracted_counts[diocese_url] = parishes_with_data_extracted_counts.get(diocese_url, 0) + 1

        for diocese in dioceses:
            diocese["parish_directory_url"] = dir_url_map.get(diocese["id"])
            diocese["parishes_in_db_count"] = parish_counts.get(diocese["Website"], 0)
            diocese["parishes_with_data_extracted_count"] = parishes_with_data_extracted_counts.get(diocese["Website"], 0)

            # Add blocking detection data
            blocking_data = blocking_data_map.get(diocese["id"], {})
            diocese["is_blocked"] = blocking_data.get("is_blocked", False)
            diocese["blocking_type"] = blocking_data.get("blocking_type")
            diocese["blocking_evidence"] = blocking_data.get("blocking_evidence", {})
            diocese["status_code"] = blocking_data.get("status_code")
            diocese["robots_txt_check"] = blocking_data.get("robots_txt_check", {})
            diocese["respectful_automation_used"] = blocking_data.get("respectful_automation_used", False)
            diocese["status_description"] = blocking_data.get("status_description", "Not tested")

        # Sort in Python
        reverse = sort_order.lower() == "desc"
        if sort_by == "parishes_in_db_count":
            dioceses.sort(key=lambda d: d.get("parishes_in_db_count", 0), reverse=reverse)
        else:
            # Use .get for safer access and handle None values
            dioceses.sort(key=lambda d: (d.get(sort_by) is None, d.get(sort_by, "")), reverse=reverse)

        # Paginate the sorted list
        paginated_dioceses = dioceses[offset : offset + page_size]

        return {"data": paginated_dioceses, "total_count": total_count, "page": page, "page_size": page_size}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/dioceses/{diocese_id}")
def get_diocese(diocese_id: int):
    """
    Fetches a single diocese by its ID.
    """
    try:
        response = supabase.table("Dioceses").select("*").eq("id", diocese_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Diocese not found")
        return {"data": response.data[0]}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/dioceses/{diocese_id}/parishes")
def get_parishes_for_diocese(
    diocese_id: int,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "Name",
    sort_order: str = "asc",
    filter_name: str = None,
    filter_website: str = None,
    filter_data_extracted: str = None,
    filter_data_available: str = None,
    filter_blocked: str = None,
    filter_diocese_name: str = None,
):
    """
    Fetches all parishes for a given diocese ID with pagination, sorting, and filtering.
    """
    try:
        offset = (page - 1) * page_size

        # First, get the diocese's website using its ID
        diocese_response = supabase.table("Dioceses").select("Website").eq("id", diocese_id).execute()
        if not diocese_response.data:
            raise HTTPException(status_code=404, detail="Diocese not found")
        diocese_website = diocese_response.data[0]["Website"]

        query = supabase.table("parishes_with_diocese_name").select("*", count="exact").eq("diocese_id", diocese_id)

        # Apply filters
        if filter_name:
            query = query.ilike("Name", f"%{filter_name}%")
        if filter_diocese_name:
            query = query.ilike("diocese_name", f"%{filter_diocese_name}%")

        if filter_website:
            query = query.ilike("Web", f"%{filter_website}%")  # Use 'Web' for website column

        if filter_blocked:
            if filter_blocked.lower() == "true":
                query = query.eq("is_blocked", True)
            elif filter_blocked.lower() == "false":
                query = query.eq("is_blocked", False)

        # Handle data_extracted and data_available filters by pre-filtering parish IDs
        if filter_data_extracted or filter_data_available:
            # Get all parishes with data
            all_parish_data_response = supabase.table("ParishData").select("parish_id, fact_value").execute()
            parishes_with_data = {
                item["parish_id"]
                for item in all_parish_data_response.data
                if item["fact_value"] and item["fact_value"] != "Information not found"
            }

            # Determine which parish IDs to filter by
            filter_parish_ids = None
            if filter_data_extracted:
                if filter_data_extracted.lower() == "true":
                    filter_parish_ids = list(parishes_with_data)
                elif filter_data_extracted.lower() == "false":
                    # Get all parish IDs for this diocese, then subtract those with data
                    all_parishes_response = (
                        supabase.table("parishes_with_diocese_name").select("id").eq("diocese_id", diocese_id).execute()
                    )
                    all_parish_ids = {p["id"] for p in all_parishes_response.data}
                    filter_parish_ids = list(all_parish_ids - parishes_with_data)
            elif filter_data_available:
                if filter_data_available.lower() == "true":
                    filter_parish_ids = list(parishes_with_data)
                elif filter_data_available.lower() == "false":
                    # Get all parish IDs for this diocese, then subtract those with data
                    all_parishes_response = (
                        supabase.table("parishes_with_diocese_name").select("id").eq("diocese_id", diocese_id).execute()
                    )
                    all_parish_ids = {p["id"] for p in all_parishes_response.data}
                    filter_parish_ids = list(all_parish_ids - parishes_with_data)

            # Apply the parish ID filter to the query
            if filter_parish_ids is not None:
                if len(filter_parish_ids) == 0:
                    # No parishes match the criteria, return empty result
                    return {"data": [], "total_count": 0, "page": page, "page_size": page_size}
                query = query.in_("id", filter_parish_ids)

        # Apply sorting and pagination
        if sort_by == "Name":
            query = query.order("Name", desc=sort_order.lower() == "desc")
        elif sort_by == "DioceseName":
            query = query.order("diocese_name", desc=sort_order.lower() == "desc")

        parishes_response = query.range(offset, offset + page_size - 1).execute()

        parishes = parishes_response.data
        total_count = parishes_response.count

        if not parishes:
            return {"data": [], "total_count": 0, "page": page, "page_size": page_size}

        parish_ids = [parish["id"] for parish in parishes]

        # Fetch all reconciliation and adoration facts for all parishes in a single query
        parish_data_response = (
            supabase.table("ParishData")
            .select("parish_id, fact_type, fact_value")
            .in_("parish_id", parish_ids)
            .in_("fact_type", ["ReconciliationSchedule", "AdorationSchedule"])
            .execute()
        )
        parish_data = parish_data_response.data

        # Create a lookup for parish facts
        parish_facts = {}
        for fact in parish_data:
            pid = fact["parish_id"]
            if pid not in parish_facts:
                parish_facts[pid] = {}
            if fact["fact_type"] == "ReconciliationSchedule":
                parish_facts[pid]["reconciliation_facts"] = fact["fact_value"]
            elif fact["fact_type"] == "AdorationSchedule":
                parish_facts[pid]["adoration_facts"] = fact["fact_value"]

        # Add facts to parishes and data_extracted flag
        all_parishes_with_data = {
            item["parish_id"] for item in parish_data if item["fact_value"] and item["fact_value"] != "Information not found"
        }

        for parish in parishes:
            facts = parish_facts.get(parish["id"], {})
            parish["reconciliation_facts"] = facts.get("reconciliation_facts")
            parish["adoration_facts"] = facts.get("adoration_facts")
            parish["data_extracted"] = parish["id"] in all_parishes_with_data

            # Map database column names to frontend expectations
            if "Web" in parish:
                parish["Website"] = parish["Web"]

            # Ensure blocking detection fields are present
            parish["is_blocked"] = parish.get("is_blocked", False)
            parish["blocking_type"] = parish.get("blocking_type")
            parish["blocking_evidence"] = parish.get("blocking_evidence", {})
            parish["status_code"] = parish.get("status_code")
            parish["robots_txt_check"] = parish.get("robots_txt_check", {})
            parish["respectful_automation_used"] = parish.get("respectful_automation_used", False)
            parish["status_description"] = parish.get("status_description", "Not tested")

        if filter_data_extracted:
            if filter_data_extracted.lower() == "true":
                parishes = [p for p in parishes if p["data_extracted"]]
            elif filter_data_extracted.lower() == "false":
                parishes = [p for p in parishes if not p["data_extracted"]]

        if filter_data_available:
            if filter_data_available.lower() == "true":
                parishes = [p for p in parishes if p["data_extracted"]]
            elif filter_data_available.lower() == "false":
                parishes = [p for p in parishes if not p["data_extracted"]]

        if filter_blocked:
            if filter_blocked.lower() == "true":
                parishes = [p for p in parishes if p.get("is_blocked", False)]
            elif filter_blocked.lower() == "false":
                parishes = [p for p in parishes if not p.get("is_blocked", False)]

        # Apply Python-side sorting for data_extracted and is_blocked if requested
        if sort_by == "data_extracted":
            parishes.sort(key=lambda p: p.get("data_extracted", False), reverse=sort_order.lower() == "desc")
        elif sort_by == "is_blocked":
            parishes.sort(key=lambda p: p.get("is_blocked", False), reverse=sort_order.lower() == "desc")

        return {"data": parishes, "total_count": total_count, "page": page, "page_size": page_size}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/parishes")
def get_all_parishes(
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "Name",
    sort_order: str = "asc",
    filter_name: str = None,
    filter_website: str = None,
    filter_data_extracted: str = None,
    filter_data_available: str = None,
    filter_blocked: str = None,
    filter_diocese_name: str = None,
):
    """
    Fetches all parishes with pagination, sorting, and filtering.
    """
    try:
        offset = (page - 1) * page_size

        query = supabase.table("parishes_with_diocese_name").select("*", count="exact")

        # Apply filters
        if filter_name:
            query = query.ilike("Name", f"%{filter_name}%")
        if filter_diocese_name:
            query = query.ilike("diocese_name", f"%{filter_diocese_name}%")

        if filter_website:
            query = query.ilike("Website", f"%{filter_website}%")

        if filter_blocked:
            if filter_blocked.lower() == "true":
                query = query.eq("is_blocked", True)
            elif filter_blocked.lower() == "false":
                query = query.eq("is_blocked", False)

        # Handle data_extracted and data_available filters by pre-filtering parish IDs
        if filter_data_extracted or filter_data_available:
            # Get all parishes with data
            all_parish_data_response = supabase.table("ParishData").select("parish_id, fact_value").execute()
            parishes_with_data = {
                item["parish_id"]
                for item in all_parish_data_response.data
                if item["fact_value"] and item["fact_value"] != "Information not found"
            }

            # Determine which parish IDs to filter by
            filter_parish_ids = None
            if filter_data_extracted:
                if filter_data_extracted.lower() == "true":
                    filter_parish_ids = list(parishes_with_data)
                elif filter_data_extracted.lower() == "false":
                    # Get all parish IDs from the current query, then subtract those with data
                    all_parishes_response = supabase.table("parishes_with_diocese_name").select("id").execute()
                    all_parish_ids = {p["id"] for p in all_parishes_response.data}
                    filter_parish_ids = list(all_parish_ids - parishes_with_data)
            elif filter_data_available:
                if filter_data_available.lower() == "true":
                    filter_parish_ids = list(parishes_with_data)
                elif filter_data_available.lower() == "false":
                    # Get all parish IDs from the current query, then subtract those with data
                    all_parishes_response = supabase.table("parishes_with_diocese_name").select("id").execute()
                    all_parish_ids = {p["id"] for p in all_parishes_response.data}
                    filter_parish_ids = list(all_parish_ids - parishes_with_data)

            # Apply the parish ID filter to the query
            if filter_parish_ids is not None:
                if len(filter_parish_ids) == 0:
                    # No parishes match the criteria, return empty result
                    return {"data": [], "total_count": 0, "page": page, "page_size": page_size}
                query = query.in_("id", filter_parish_ids)

        # Apply sorting and pagination
        if sort_by == "Name":
            query = query.order("Name", desc=sort_order.lower() == "desc")
        elif sort_by == "DioceseName":
            query = query.order("diocese_name", desc=sort_order.lower() == "desc")
        elif sort_by == "Web":
            query = query.order("Web", desc=sort_order.lower() == "desc")
        elif sort_by == "is_blocked":
            query = query.order("is_blocked", desc=sort_order.lower() == "desc")
        # Add other sortable columns as needed

        parishes_response = query.range(offset, offset + page_size - 1).execute()

        parishes = parishes_response.data
        total_count = parishes_response.count

        # Fetch parish data for 'data_extracted' filter and add data_extracted flag
        all_parish_ids = [p["id"] for p in parishes]
        all_parish_data_response = (
            supabase.table("ParishData").select("parish_id, fact_value").in_("parish_id", all_parish_ids).execute()
        )
        all_parishes_with_data = {
            item["parish_id"]
            for item in all_parish_data_response.data
            if item["fact_value"] and item["fact_value"] != "Information not found"
        }

        for parish in parishes:
            parish["data_extracted"] = parish["id"] in all_parishes_with_data

            # Map database column names to frontend expectations

            if "Web" in parish:
                parish["Website"] = parish["Web"]

            # Ensure blocking detection fields are present
            parish["is_blocked"] = parish.get("is_blocked", False)
            parish["blocking_type"] = parish.get("blocking_type")
            parish["blocking_evidence"] = parish.get("blocking_evidence", {})
            parish["status_code"] = parish.get("status_code")
            parish["robots_txt_check"] = parish.get("robots_txt_check", {})
            parish["respectful_automation_used"] = parish.get("respectful_automation_used", False)
            parish["status_description"] = parish.get("status_description", "Not tested")

        # Apply filter for data_extracted after computing the flag
        if filter_data_extracted:
            if filter_data_extracted.lower() == "true":
                parishes = [p for p in parishes if p["data_extracted"]]
            elif filter_data_extracted.lower() == "false":
                parishes = [p for p in parishes if not p["data_extracted"]]

        if filter_data_available:
            if filter_data_available.lower() == "true":
                parishes = [p for p in parishes if p["data_extracted"]]
            elif filter_data_available.lower() == "false":
                parishes = [p for p in parishes if not p["data_extracted"]]

        if filter_blocked:
            if filter_blocked.lower() == "true":
                parishes = [p for p in parishes if p.get("is_blocked", False)]
            elif filter_blocked.lower() == "false":
                parishes = [p for p in parishes if not p.get("is_blocked", False)]

        # Apply Python-side sorting for data_extracted and is_blocked if requested
        if sort_by == "data_extracted":
            parishes.sort(key=lambda p: p.get("data_extracted", False), reverse=sort_order.lower() == "desc")
        elif sort_by == "is_blocked":
            parishes.sort(key=lambda p: p.get("is_blocked", False), reverse=sort_order.lower() == "desc")

        return {"data": parishes, "total_count": total_count, "page": page, "page_size": page_size}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/parish")
def get_parish(parish_id: int):
    """
    Fetches a single parish by its ID with diocese name and schedule data.
    """
    try:
        # Get parish basic info
        parish_response = supabase.table("Parishes").select("*").eq("id", parish_id).execute()

        if not parish_response.data:
            raise HTTPException(status_code=404, detail="Parish not found")

        parish = parish_response.data[0]

        # Get diocese name
        if parish.get("diocese_id"):
            diocese_response = supabase.table("Dioceses").select("Name").eq("id", parish["diocese_id"]).execute()
            if diocese_response.data:
                parish["diocese_name"] = diocese_response.data[0]["Name"]
            else:
                parish["diocese_name"] = None
        else:
            parish["diocese_name"] = None

        # Get schedule data
        schedule_response = supabase.table("ParishData").select("*").eq("parish_id", parish_id).execute()

        # Add schedule data to parish
        parish["schedules"] = schedule_response.data

        return {"data": parish}
    except Exception as e:
        return {"error": str(e)}


# WebSocket endpoint for real-time monitoring
@app.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring updates"""
    await websocket.accept()
    await monitoring_manager.add_connection(websocket)

    try:
        while True:
            # Keep connection alive and handle any incoming messages
            try:
                data = await websocket.receive_text()
                # Handle any client messages if needed
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

    except WebSocketDisconnect:
        pass
    finally:
        await monitoring_manager.remove_connection(websocket)


# Monitoring API endpoints
@app.get("/api/monitoring/status")
async def get_monitoring_status():
    """Get current monitoring status with staleness checking"""
    return {
        "system_health": monitoring_manager.get_system_health(),
        "extraction_status": await monitoring_manager.get_current_extraction_status(),
        "circuit_breakers": await monitoring_manager.get_current_circuit_breakers(),
        "performance_metrics": monitoring_manager.performance_metrics,
        "recent_errors": monitoring_manager.recent_errors[:10],  # Last 10 errors
        "extraction_history": monitoring_manager.extraction_history[:10],  # Last 10 extractions
        "websocket_connections": len(monitoring_manager.websocket_connections),
    }


@app.post("/api/monitoring/extraction_status")
async def update_extraction_status_endpoint(status_data: dict):
    """Update extraction status (for async extraction scripts to call)"""
    try:
        await monitoring_manager.update_extraction_status(status_data)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/monitoring/circuit_breakers")
async def update_circuit_breakers_endpoint(circuit_data: dict):
    """Update circuit breaker status (for async extraction scripts to call)"""
    try:
        await monitoring_manager.update_circuit_breakers(circuit_data)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/monitoring/performance")
async def update_performance_metrics_endpoint(metrics_data: dict):
    """Update performance metrics (for async extraction scripts to call)"""
    try:
        await monitoring_manager.update_performance_metrics(metrics_data)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/monitoring/error")
async def report_error_endpoint(error_data: dict):
    """Report an error (for async extraction scripts to call)"""
    try:
        await monitoring_manager.add_error(error_data)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/monitoring/extraction_complete")
async def report_extraction_complete_endpoint(extraction_data: dict):
    """Report completed extraction (for async extraction scripts to call)"""
    try:
        await monitoring_manager.add_extraction_complete(extraction_data)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/monitoring/log")
async def send_log_endpoint(log_data: dict):
    """Send live log entry (for async extraction scripts to call)"""
    try:
        await monitoring_manager.send_live_log(log_data)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


# Multi-worker endpoints
@app.post("/api/monitoring/worker/{worker_id}/extraction_status")
async def update_worker_extraction_status(worker_id: str, status_data: dict):
    """Update extraction status for a specific worker"""
    try:
        await monitoring_manager.update_worker_extraction_status(worker_id, status_data)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/monitoring/worker/{worker_id}/circuit_breakers")
async def update_worker_circuit_breakers(worker_id: str, circuit_data: dict):
    """Update circuit breaker status for a specific worker"""
    try:
        await monitoring_manager.update_worker_circuit_breakers(worker_id, circuit_data)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/monitoring/workers")
async def get_workers():
    """Get list of all workers"""
    try:
        return {"workers": monitoring_manager.get_worker_list(), "aggregate_mode": monitoring_manager.aggregate_mode}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/monitoring/worker/{worker_id}")
async def get_worker_details(worker_id: str):
    """Get detailed status for a specific worker"""
    try:
        if worker_id not in monitoring_manager.workers:
            raise HTTPException(status_code=404, detail="Worker not found")

        worker_data = monitoring_manager.workers[worker_id]
        return {
            "worker_id": worker_id,
            "extraction_status": worker_data["extraction_status"],
            "circuit_breakers": worker_data["circuit_breakers"],
            "performance_metrics": worker_data["performance_metrics"],
            "last_updated": worker_data["last_updated"],
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/monitoring/mode/{mode}")
async def set_monitoring_mode(mode: str):
    """Switch between aggregate and individual worker view"""
    try:
        if mode not in ["aggregate", "individual"]:
            raise HTTPException(status_code=400, detail="Mode must be 'aggregate' or 'individual'")

        monitoring_manager.aggregate_mode = mode == "aggregate"
        return {"status": "success", "mode": mode}
    except Exception as e:
        return {"error": str(e)}
