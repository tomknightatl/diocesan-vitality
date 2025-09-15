# Real-time Monitoring Dashboard

## Overview

The real-time monitoring dashboard provides **live operational visibility** into the Diocesan Vitality parish extraction system. It displays real-time extraction progress, system health, circuit breaker status, performance metrics, and error tracking through an intuitive web interface.

## Features

### 📊 **Real-time System Monitoring**
- **System Health**: CPU usage, memory utilization, uptime tracking
- **Extraction Status**: Live progress with parishes processed and success rates
- **Performance Metrics**: Parishes per minute, queue size, pool utilization
- **Alert System**: Real-time error notifications and warnings

### 🛡️ **Circuit Breaker Visualization**
- **Circuit States**: CLOSED/OPEN/HALF-OPEN status for all circuit breakers
- **Statistics**: Request counts, success rates, failure tracking
- **Real-time Updates**: Instant notification of circuit state changes
- **Historical Data**: Blocked requests and recovery patterns

### 📈 **Performance Analytics**
- **Live Metrics**: Real-time performance tracking and trends
- **Extraction History**: Recent extraction results and success rates
- **Resource Utilization**: WebDriver pool usage and efficiency
- **Throughput Analysis**: Parishes processed per minute trends

### 🚨 **Error Tracking & Alerts**
- **Live Error Feed**: Real-time error notifications with severity levels
- **Error Classification**: Categorized by type (parsing, network, timeout)
- **Diocese Context**: Error tracking per diocese for targeted debugging
- **Error History**: Recent error patterns and frequency analysis

### 📋 **Live Extraction Log**
- **Real-time Logging**: Live stream of extraction activities
- **Log Levels**: INFO, WARNING, ERROR with color coding
- **Searchable History**: Scrollable log with timestamp filtering
- **Module Tracking**: Log entries categorized by extraction module

## Architecture

### Frontend (React)
- **Dashboard.jsx**: Main dashboard component with real-time updates
- **WebSocket Client**: Live connection to monitoring backend
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Bootstrap UI**: Professional interface with charts and indicators

### Backend (FastAPI)
- **WebSocket Server**: Real-time data broadcasting to connected clients
- **Monitoring API**: REST endpoints for extraction scripts to report status
- **System Health**: Automatic system metrics collection and broadcasting
- **Connection Management**: Multiple client support with automatic reconnection

### Integration
- **MonitoringClient**: Easy integration for extraction scripts
- **Context Managers**: Automatic monitoring for extraction workflows
- **Circuit Breaker Integration**: Direct reporting from circuit breaker system
- **Error Reporting**: Centralized error collection and broadcasting

## Usage

### Accessing the Dashboard

**Complete Setup Instructions:**

1. **Activate Virtual Environment** (if using monitored pipeline):
   ```bash
   source venv/bin/activate
   ```

2. **Start the Backend Server** (in separate terminal):
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start the Frontend Server** (in separate terminal):
   ```bash
   cd frontend
   npm run dev
   ```

4. **Open Dashboard**:
   Navigate to `http://localhost:5173/dashboard`

5. **Run Monitoring-Enabled Pipeline**:
   ```bash
   # Basic run with monitoring and 2-hour timeout
   source venv/bin/activate && timeout 7200 python3 run_pipeline.py --max_parishes_per_diocese 10 --num_parishes_for_schedule 10
   
   # Or test dashboard functionality
   python3 test_dashboard.py --mode extraction
   ```

### Integration with Extraction Scripts

#### Basic Integration
```python
from core.monitoring_client import get_monitoring_client

# Get monitoring client
client = get_monitoring_client("http://localhost:8000")

# Report extraction start
client.extraction_started("Archdiocese of Atlanta", 25)

# Update progress
client.extraction_progress("Archdiocese of Atlanta", 10, 25, 85.0)

# Report completion
client.extraction_finished("Archdiocese of Atlanta", 24, 96.0, 145.5)
```

#### Context Manager (Recommended)
```python
from core.monitoring_client import ExtractionMonitoring

# Automatic monitoring with context manager
with ExtractionMonitoring("Archdiocese of Atlanta", 25) as monitor:
    for i, parish in enumerate(parishes):
        # Process parish...
        successful = process_parish(parish)
        
        # Update progress automatically
        monitor.update_progress(i + 1, successful_count)
```

#### Circuit Breaker Integration
```python
# Report circuit breaker events
client.circuit_breaker_opened("diocese_page_load", "Multiple timeouts")
client.circuit_breaker_closed("diocese_page_load")

# Update circuit breaker status
circuit_status = {
    "diocese_page_load": {
        "state": "CLOSED",
        "total_requests": 45,
        "success_rate": "95.6%",
        "total_failures": 2,
        "total_blocked": 0
    }
}
client.update_circuit_breakers(circuit_status)
```

## API Endpoints

### WebSocket
- **`/ws/monitoring`**: WebSocket endpoint for real-time updates

### REST API
- **`GET /api/monitoring/status`**: Get current monitoring status
- **`POST /api/monitoring/extraction_status`**: Update extraction status
- **`POST /api/monitoring/circuit_breakers`**: Update circuit breaker status
- **`POST /api/monitoring/performance`**: Update performance metrics
- **`POST /api/monitoring/error`**: Report an error
- **`POST /api/monitoring/extraction_complete`**: Report extraction completion
- **`POST /api/monitoring/log`**: Send live log entry

## Dashboard Components

### System Health Card
```
🔹 System Health
   Status: ✅ Healthy
   CPU: 45.2%
   Memory: 62.8%
   Uptime: 2h 34m
```

### Extraction Status Card
```
🔹 Extraction Status
   Status: RUNNING
   Diocese: Archdiocese of Atlanta
   Parishes: 15/25
   Success Rate: 92%
```

### Performance Metrics Card
```
🔹 Performance
   25.3 Parishes/min
   Queue: 3
   Pool: 75%
```

### Alerts Card
```
🔹 Alerts
   2 Recent Errors
   Last: 14:32:15
```

### Circuit Breaker Grid
```
🛡️ Circuit Breaker Status

┌─ diocese_page_load ────────┐
│ Status: CLOSED ✅          │
│ Requests: 45               │
│ Success: 95.6%             │
│ Failures: 2                │
└────────────────────────────┘

┌─ parish_detail_load ──────┐
│ Status: HALF_OPEN ⚠️       │
│ Requests: 89               │  
│ Success: 87.5%             │
│ Blocked: 3                 │
└────────────────────────────┘
```

### Live Log Stream
```
📋 Live Extraction Log

[14:32:45] 🚀 Started extraction for Archdiocese of Atlanta (25 parishes)
[14:32:47] 📊 Progress: 5/25 parishes (20.0%)
[14:32:49] ✅ Extracted parish 8: Enhanced data found
[14:32:51] ⚠️ Parish 12: Partial data extracted
[14:32:53] 🚫 Circuit breaker 'webdriver_requests' OPEN: Multiple timeouts
```

## Testing

### Test Dashboard Functionality
```bash
# Activate virtual environment first
source venv/bin/activate

# Basic monitoring test
python3 test_dashboard.py --mode basic

# Extraction simulation test (recommended)
python3 test_dashboard.py --mode extraction

# Continuous monitoring demo
python3 test_dashboard.py --mode continuous
```

**Note:** Ensure backend server is running before testing dashboard functionality.

### Manual Testing
1. Open dashboard in browser
2. Run test script to simulate extraction
3. Observe real-time updates:
   - System health changes
   - Extraction progress
   - Circuit breaker state changes
   - Live log entries
   - Error notifications

## Configuration

### Environment Variables
```bash
# Backend configuration
MONITORING_HOST=localhost
MONITORING_PORT=8000
WEBSOCKET_KEEPALIVE=10

# Frontend configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

### Monitoring Client Configuration
```python
# Configure monitoring client
client = MonitoringClient("http://localhost:8000")

# Disable monitoring for testing
client.disable()

# Enable monitoring
client.enable()
```

## Troubleshooting

### Dashboard Not Connecting
1. **Check Backend Status**:
   ```bash
   curl http://localhost:8000/api/monitoring/status
   ```

2. **Verify WebSocket Endpoint**:
   ```bash
   wscat -c ws://localhost:8000/ws/monitoring
   ```

3. **Check Network Configuration**:
   - Ensure ports 8000 (backend) and 5173 (frontend) are accessible
   - Verify CORS settings in backend configuration

### Missing Data
1. **Integration Issues**:
   - Ensure extraction scripts use MonitoringClient
   - Verify correct backend URL configuration
   - Check for network connectivity issues

2. **WebSocket Disconnections**:
   - Monitor browser console for WebSocket errors
   - Check for firewall or proxy issues
   - Verify backend WebSocket handling

### Performance Issues
1. **High Update Frequency**:
   - Reduce monitoring update frequency in extraction scripts
   - Implement client-side throttling for high-frequency updates

2. **Memory Usage**:
   - Monitor browser memory usage with many log entries
   - Implement log entry limits and cleanup

## Best Practices

### For Extraction Scripts
1. **Use Context Managers**: Leverage ExtractionMonitoring for automatic lifecycle management
2. **Throttle Updates**: Don't send updates for every parish - batch updates every 5-10 parishes
3. **Error Handling**: Always include try/catch around monitoring calls
4. **Graceful Degradation**: Disable monitoring if backend is unavailable

### For Dashboard Usage
1. **Multiple Tabs**: Dashboard supports multiple concurrent viewers
2. **Mobile Access**: Dashboard is responsive and works on mobile devices
3. **Real-time Alerts**: Keep dashboard open during production runs for immediate issue notification
4. **Historical Analysis**: Use extraction history for performance trend analysis

## Integration with Async Extraction

The monitoring dashboard integrates seamlessly with the async concurrent extraction system:

```python
# In async_extract_parishes.py
from core.monitoring_client import ExtractionMonitoring

async def process_diocese_async(diocese_info, num_parishes):
    with ExtractionMonitoring(diocese_info['name'], num_parishes) as monitor:
        # Async extraction with real-time monitoring
        async for parish_result in extract_parishes_concurrent(diocese_info):
            monitor.update_progress(parish_result.processed, parish_result.successful)
```

This provides **complete visibility** into the high-performance async extraction process with real-time updates, circuit breaker status, and performance analytics.

## Production Deployment

### Docker Configuration
```dockerfile
# Backend monitoring
EXPOSE 8000
ENV MONITORING_ENABLED=true

# Frontend dashboard
EXPOSE 5173
ENV VITE_MONITORING_URL=https://api.yourdomain.com
```

### Kubernetes Deployment
```yaml
# WebSocket service configuration
spec:
  ports:
    - name: http
      port: 8000
      targetPort: 8000
    - name: websocket
      port: 8001
      targetPort: 8001
```

The real-time monitoring dashboard provides **enterprise-grade operational visibility** for the Diocesan Vitality parish extraction system, enabling proactive monitoring, rapid issue resolution, and performance optimization.