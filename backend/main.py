import os
import json
import asyncio
import psutil
import time
from datetime import datetime, timezone
from typing import Dict, List, Set
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from dotenv import load_dotenv
from supabase import create_client, Client
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

# Load .env file from the project root
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Global monitoring state
class MonitoringManager:
    def __init__(self):
        self.websocket_connections: Set[WebSocket] = set()
        self.start_time = time.time()
        self.extraction_status = {
            "status": "idle",
            "current_diocese": None,
            "parishes_processed": 0,
            "total_parishes": 0,
            "success_rate": 0,
            "started_at": None,
            "progress_percentage": 0,
            "estimated_completion": None
        }
        self.circuit_breakers = {}
        self.performance_metrics = {
            "parishes_per_minute": 0,
            "queue_size": 0,
            "pool_utilization": 0,
            "total_requests": 0,
            "successful_requests": 0
        }
        self.recent_errors = []
        self.extraction_history = []
        self.max_errors = 50

    async def add_connection(self, websocket: WebSocket):
        """Add a new WebSocket connection"""
        self.websocket_connections.add(websocket)
        print(f"New WebSocket connection added. Total: {len(self.websocket_connections)}")

        # Send initial state to new connection
        await self.send_to_connection(websocket, {
            "type": "system_health",
            "payload": self.get_system_health()
        })
        await self.send_to_connection(websocket, {
            "type": "extraction_status",
            "payload": self.extraction_status
        })
        await self.send_to_connection(websocket, {
            "type": "circuit_breaker_status",
            "payload": self.circuit_breakers
        })
        await self.send_to_connection(websocket, {
            "type": "performance_metrics",
            "payload": self.performance_metrics
        })

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
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def update_extraction_status(self, status_data: Dict):
        """Update and broadcast extraction status"""
        self.extraction_status.update(status_data)
        await self.broadcast({
            "type": "extraction_status",
            "payload": self.extraction_status
        })

    async def update_circuit_breakers(self, circuit_data: Dict):
        """Update and broadcast circuit breaker status"""
        self.circuit_breakers.update(circuit_data)
        await self.broadcast({
            "type": "circuit_breaker_status",
            "payload": self.circuit_breakers
        })

    async def update_performance_metrics(self, metrics_data: Dict):
        """Update and broadcast performance metrics"""
        self.performance_metrics.update(metrics_data)
        await self.broadcast({
            "type": "performance_metrics",
            "payload": self.performance_metrics
        })

    async def add_error(self, error_data: Dict):
        """Add error to recent errors and broadcast"""
        error_entry = {
            **error_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.recent_errors.insert(0, error_entry)
        self.recent_errors = self.recent_errors[:self.max_errors]

        await self.broadcast({
            "type": "error_alert",
            "payload": error_entry
        })

    async def add_extraction_complete(self, extraction_data: Dict):
        """Add completed extraction to history"""
        extraction_entry = {
            **extraction_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.extraction_history.insert(0, extraction_entry)
        self.extraction_history = self.extraction_history[:20]  # Keep last 20

        await self.broadcast({
            "type": "extraction_complete",
            "payload": extraction_entry
        })

    async def send_live_log(self, log_data: Dict):
        """Send live log entry to all connections"""
        log_entry = {
            **log_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast({
            "type": "live_log",
            "payload": log_entry
        })

# Global monitoring manager instance
monitoring_manager = MonitoringManager()

# Background task to periodically update system health
async def periodic_health_update():
    """Periodically broadcast system health updates"""
    while True:
        try:
            health_data = monitoring_manager.get_system_health()
            await monitoring_manager.broadcast({
                "type": "system_health",
                "payload": health_data
            })
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
    "http://usccb.diocesevitality.org",
    "https://usccb.diocesevitality.org",
    "http://localhost:3000",    # React development server
    "http://localhost:8080",
    "http://localhost:8081",
    "http://localhost:5173",    # Vite development server
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
        dir_response = supabase.table('DiocesesParishDirectory').select('parish_directory_url').execute()
        dir_data = dir_response.data
        total_dioceses_processed = len(dir_data)
        found_parish_directories = sum(1 for item in dir_data if item['parish_directory_url'] is not None)
        not_found_parish_directories = total_dioceses_processed - found_parish_directories

        # Parishes summary
        parishes_count_response = supabase.table('Parishes').select('count', count='exact').execute()
        parishes_extracted = parishes_count_response.count

        parish_data_response = supabase.table('ParishData').select('parish_id, fact_value').execute()
        parish_data = parish_data_response.data
        
        parishes_with_data_extracted = len(set(item['parish_id'] for item in parish_data if item['fact_value'] and item['fact_value'] != 'Information not found'))
        
        parishes_with_data_not_extracted = parishes_extracted - parishes_with_data_extracted

        return {
            "total_dioceses_processed": total_dioceses_processed,
            "found_parish_directories": found_parish_directories,
            "not_found_parish_directories": not_found_parish_directories,
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
    filter_website: str = None
):
    """
    Fetches records from the 'Dioceses' table with pagination, sorting, and filtering.
    """
    try:
        offset = (page - 1) * page_size
        
        query = supabase.table('Dioceses').select('*')
        dioceses = query.execute().data

        # Apply filtering in Python
        if filter_name:
            dioceses = [d for d in dioceses if filter_name.lower() in d.get('Name', '').lower()]
        if filter_address:
            dioceses = [d for d in dioceses if filter_address.lower() in d.get('Address', '').lower()]
        if filter_website:
            dioceses = [d for d in dioceses if filter_website.lower() in d.get('Website', '').lower()]

        total_count = len(dioceses)

        # Fetch additional data
        all_dir_response = supabase.table('DiocesesParishDirectory').select('diocese_id, parish_directory_url').execute()
        dir_url_map = {item['diocese_id']: item['parish_directory_url'] for item in all_dir_response.data}

        parishes_response = supabase.table('Parishes').select('id, diocese_url').execute()
        parishes_map = {p['id']: p['diocese_url'] for p in parishes_response.data}
        parish_counts = {}
        for parish in parishes_response.data:
            url = parish['diocese_url']
            parish_counts[url] = parish_counts.get(url, 0) + 1

        parish_data_response = supabase.table('ParishData').select('parish_id, fact_value').execute()
        parishes_with_data = {item['parish_id'] for item in parish_data_response.data if item['fact_value'] and item['fact_value'] != 'Information not found'}

        parishes_with_data_extracted_counts = {}
        for parish_id in parishes_with_data:
            if parish_id in parishes_map:
                diocese_url = parishes_map[parish_id]
                parishes_with_data_extracted_counts[diocese_url] = parishes_with_data_extracted_counts.get(diocese_url, 0) + 1

        for diocese in dioceses:
            diocese['parish_directory_url'] = dir_url_map.get(diocese['id'])
            diocese['parishes_in_db_count'] = parish_counts.get(diocese['Website'], 0)
            diocese['parishes_with_data_extracted_count'] = parishes_with_data_extracted_counts.get(diocese['Website'], 0)

        # Sort in Python
        reverse = sort_order.lower() == 'desc'
        if sort_by == 'parishes_in_db_count':
            dioceses.sort(key=lambda d: d.get('parishes_in_db_count', 0), reverse=reverse)
        else:
            # Use .get for safer access and handle None values
            dioceses.sort(key=lambda d: (d.get(sort_by) is None, d.get(sort_by, '')), reverse=reverse)


        # Paginate the sorted list
        paginated_dioceses = dioceses[offset:offset + page_size]

        return {
            "data": paginated_dioceses,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/dioceses/{diocese_id}")
def get_diocese(diocese_id: int):
    """
    Fetches a single diocese by its ID.
    """
    try:
        response = supabase.table('Dioceses').select('*').eq('id', diocese_id).execute()
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
    filter_address: str = None,
    filter_website: str = None,
    filter_data_extracted: str = None
):
    """
    Fetches all parishes for a given diocese ID with pagination, sorting, and filtering.
    """
    try:
        offset = (page - 1) * page_size

        # First, get the diocese's website using its ID
        diocese_response = supabase.table('Dioceses').select('Website').eq('id', diocese_id).execute()
        if not diocese_response.data:
            raise HTTPException(status_code=404, detail="Diocese not found")
        diocese_website = diocese_response.data[0]['Website']

        query = supabase.table('Parishes').select('*', count='exact').eq('diocese_url', diocese_website)

        # Apply filters
        if filter_name:
            query = query.ilike('Name', f'%{filter_name}%')
        if filter_address:
            query = query.ilike('Address', f'%{filter_address}%')
        if filter_website:
            query = query.ilike('Web', f'%{filter_website}%') # Use 'Web' for website column

        # Apply sorting and pagination
        if sort_by == "Name":
            query = query.order('Name', desc=sort_order.lower() == 'desc')
        elif sort_by == "Address":
            query = query.order('Street Address', desc=sort_order.lower() == 'desc')
        elif sort_by == "Website":
            query = query.order('Web', desc=sort_order.lower() == 'desc')
        # Add other sortable columns as needed

        parishes_response = query.range(offset, offset + page_size - 1).execute()
        
        parishes = parishes_response.data
        total_count = parishes_response.count

        if not parishes:
            return {"data": [], "total_count": 0, "page": page, "page_size": page_size}

        parish_ids = [parish['id'] for parish in parishes]

        # Fetch all reconciliation and adoration facts for all parishes in a single query
        parish_data_response = supabase.table('ParishData').select('parish_id, fact_type, fact_value').in_('parish_id', parish_ids).in_('fact_type', ['ReconciliationSchedule', 'AdorationSchedule']).execute()
        parish_data = parish_data_response.data

        # Create a lookup for parish facts
        parish_facts = {}
        for fact in parish_data:
            pid = fact['parish_id']
            if pid not in parish_facts:
                parish_facts[pid] = {}
            if fact['fact_type'] == 'ReconciliationSchedule':
                parish_facts[pid]['reconciliation_facts'] = fact['fact_value']
            elif fact['fact_type'] == 'AdorationSchedule':
                parish_facts[pid]['adoration_facts'] = fact['fact_value']

        # Add facts to parishes and data_extracted flag
        all_parishes_with_data = {item['parish_id'] for item in parish_data if item['fact_value'] and item['fact_value'] != 'Information not found'}

        for parish in parishes:
            facts = parish_facts.get(parish['id'], {})
            parish['reconciliation_facts'] = facts.get('reconciliation_facts')
            parish['adoration_facts'] = facts.get('adoration_facts')
            parish['data_extracted'] = parish['id'] in all_parishes_with_data

        if filter_data_extracted:
            if filter_data_extracted.lower() == 'true':
                parishes = [p for p in parishes if p['data_extracted']]
            elif filter_data_extracted.lower() == 'false':
                parishes = [p for p in parishes if not p['data_extracted']]

        # Apply Python-side sorting for data_extracted if requested
        if sort_by == "data_extracted":
            parishes.sort(key=lambda p: p.get('data_extracted', False), reverse=sort_order.lower() == 'desc')

        return {
            "data": parishes,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/parishes")
def get_all_parishes(
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "Name",
    sort_order: str = "asc",
    filter_name: str = None,
    filter_address: str = None,
    filter_website: str = None,
    filter_data_extracted: str = None
):
    """
    Fetches all parishes with pagination, sorting, and filtering.
    """
    try:
        offset = (page - 1) * page_size
        
        query = supabase.table('Parishes').select('*', count='exact')
        
        # Apply filters
        if filter_name:
            query = query.ilike('Name', f'%{filter_name}%')
        if filter_address:
            query = query.ilike('Address', f'%{filter_address}%')
        if filter_website:
            query = query.ilike('Website', f'%{filter_website}%')

        # Apply sorting and pagination
        if sort_by == "Name":
            query = query.order('Name', desc=sort_order.lower() == 'desc')
        elif sort_by == "Address":
            query = query.order('Street Address', desc=sort_order.lower() == 'desc')
        elif sort_by == "Website":
            query = query.order('Web', desc=sort_order.lower() == 'desc')
        # Add other sortable columns as needed

        parishes_response = query.range(offset, offset + page_size - 1).execute()
        
        parishes = parishes_response.data
        total_count = parishes_response.count

        # Fetch parish data for 'data_extracted' filter and add data_extracted flag
        all_parish_ids = [p['id'] for p in parishes]
        all_parish_data_response = supabase.table('ParishData').select('parish_id, fact_value').in_('parish_id', all_parish_ids).execute()
        all_parishes_with_data = {item['parish_id'] for item in all_parish_data_response.data if item['fact_value'] and item['fact_value'] != 'Information not found'}

        for parish in parishes:
            parish['data_extracted'] = parish['id'] in all_parishes_with_data

        # Apply filter for data_extracted after computing the flag
        if filter_data_extracted:
            if filter_data_extracted.lower() == 'true':
                parishes = [p for p in parishes if p['data_extracted']]
            elif filter_data_extracted.lower() == 'false':
                parishes = [p for p in parishes if not p['data_extracted']]

        # Apply Python-side sorting for data_extracted if requested
        if sort_by == "data_extracted":
            parishes.sort(key=lambda p: p.get('data_extracted', False), reverse=sort_order.lower() == 'desc')

        return {
            "data": parishes,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/parish")
def get_parish(
    parish_id: int
):
    """
    Fetches a single parish by its ID.
    """
    try:
        response = supabase.table('Parishes').select('*').eq('id', parish_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Parish not found")
        return {"data": response.data[0]}
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
    """Get current monitoring status"""
    return {
        "system_health": monitoring_manager.get_system_health(),
        "extraction_status": monitoring_manager.extraction_status,
        "circuit_breakers": monitoring_manager.circuit_breakers,
        "performance_metrics": monitoring_manager.performance_metrics,
        "recent_errors": monitoring_manager.recent_errors[:10],  # Last 10 errors
        "extraction_history": monitoring_manager.extraction_history[:10],  # Last 10 extractions
        "websocket_connections": len(monitoring_manager.websocket_connections)
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

