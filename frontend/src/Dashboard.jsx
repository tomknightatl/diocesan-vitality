import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Card, Badge, Table, Alert, Spinner, Button } from 'react-bootstrap';
import './Dashboard.css';

const Dashboard = () => {
  // State management
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [extractionStatus, setExtractionStatus] = useState(null);
  const [circuitBreakers, setCircuitBreakers] = useState({});
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [recentErrors, setRecentErrors] = useState([]);
  const [extractionHistory, setExtractionHistory] = useState([]);
  const [liveLog, setLiveLog] = useState([]);
  const [pipelineStatus, setPipelineStatus] = useState(null);
  
  const wsRef = useRef(null);
  const maxLogEntries = 100;
  const maxErrorEntries = 20;

  // WebSocket connection management
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const hostname = window.location.hostname;
      let backendHost;

      switch (hostname) {
        case 'localhost':
        case '127.0.0.1':
          backendHost = 'localhost:8000';
          break;
        
        case 'usccb.diocesevitality.org':
          // The old frontend domain points to the old backend API
          backendHost = 'api.diocesevitality.org'; 
          break;

        case 'diocesanvitality.org':
          // The new frontend domains point to the new backend API
          backendHost = 'api.diocesanvitality.org';
          break;

        default:
          // As a fallback, default to the new production backend.
          backendHost = 'api.diocesanvitality.org';
      }

      const wsUrl = `${protocol}//${backendHost}/ws/monitoring`;

      console.log('🔌 Attempting WebSocket connection to:', wsUrl);
      console.log('🏠 Hostname:', hostname);

      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected to monitoring');
        setConnected(true);
        setConnectionStatus('connected');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 WebSocket message received:', data.type, data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
        setConnectionStatus('disconnected');
        
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.CLOSED) {
            connectWebSocket();
          }
        }, 3000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };
      
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      setConnectionStatus('error');
    }
  };

  const handleWebSocketMessage = (data) => {
    console.log('🔄 Processing message type:', data.type);
    switch (data.type) {
      case 'extraction_status':
        setExtractionStatus(data.payload);
        break;
        
      case 'circuit_breaker_status':
        setCircuitBreakers(data.payload);
        break;
        
      case 'performance_metrics':
        setPerformanceMetrics(data.payload);
        break;
        
      case 'system_health':
        setSystemHealth(data.payload);
        break;
        
      case 'error_alert':
        setRecentErrors(prev => [
          { ...data.payload, timestamp: new Date().toISOString() },
          ...prev.slice(0, maxErrorEntries - 1)
        ]);
        break;
        
      case 'extraction_complete':
        setExtractionHistory(prev => [
          data.payload,
          ...prev.slice(0, 19) // Keep last 20 extractions
        ]);
        break;
        
      case 'live_log':
        setLiveLog(prev => [
          { ...data.payload, id: Date.now() + Math.random() },
          ...prev.slice(0, maxLogEntries - 1)
        ]);
        break;

      case 'pipeline_status':
        setPipelineStatus(data.payload);
        break;
        
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      'running': 'success',
      'idle': 'secondary',
      'error': 'danger',
      'paused': 'warning',
      'completed': 'info',
      'stale': 'warning'
    };
    return variants[status] || 'secondary';
  };

  const getCircuitBreakerBadge = (state) => {
    const variants = {
      'CLOSED': 'success',
      'OPEN': 'danger',
      'HALF_OPEN': 'warning'
    };
    return variants[state] || 'secondary';
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatDecimal = (value) => {
    if (typeof value !== 'number') return value;
    return Number(value.toFixed(2));
  };

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${formatDecimal(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <Container fluid className="dashboard">
      {/* Header */}
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <h2>Current Health of Data Collection Servers</h2>
            <div className="d-flex align-items-center">
              <Badge bg={connected ? 'success' : 'danger'} className="me-2">
                {connected ? '🟢 Connected' : '🔴 Disconnected'}
              </Badge>
              <Button 
                variant="outline-primary" 
                size="sm"
                onClick={() => window.location.reload()}
              >
                🔄 Refresh
              </Button>
            </div>
          </div>
        </Col>
      </Row>

      {/* Connection Alert */}
      {!connected && (
        <Alert variant="warning" className="mb-4">
          ⚠️ Dashboard disconnected from monitoring service. Attempting to reconnect...
        </Alert>
      )}

      {/* System Health Overview */}
      <Row className="mb-4">
        <Col md={4}>
          <Card className="h-100">
            <Card.Body>
              <Card.Title className="text-center">
                <i className="fas fa-heartbeat text-danger"></i> System Health
              </Card.Title>
              {systemHealth ? (
                <div className="text-center">
                  <div className="display-6 mb-2">
                    <Badge bg={systemHealth.status === 'healthy' ? 'success' : 'warning'}>
                      {systemHealth.status === 'healthy' ? '✅' : '⚠️'}
                    </Badge>
                  </div>
                  <p className="mb-1"><strong>CPU:</strong> {formatDecimal(systemHealth.cpu_usage)}%</p>
                  <p className="mb-1"><strong>Memory:</strong> {formatDecimal(systemHealth.memory_usage)}%</p>
                  <p className="mb-0"><strong>Uptime:</strong> {formatDuration(systemHealth.uptime)}</p>
                </div>
              ) : (
                <div className="text-center">
                  <Spinner animation="border" size="sm" />
                  <p className="mt-2">Loading...</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col md={4}>
          <Card className="h-100">
            <Card.Body>
              <Card.Title className="text-center">
                <i className="fas fa-tasks text-info"></i> Extraction Status
              </Card.Title>
              <div className="text-center">
                <div className="display-6 mb-2">
                  <Badge bg={extractionStatus ? getStatusBadge(extractionStatus.status) : 'secondary'}>
                    {extractionStatus ? extractionStatus.status.toUpperCase() : 'IDLE'}
                  </Badge>
                </div>
                {extractionStatus && extractionStatus.status === 'stale' && extractionStatus.stale_reason && (
                  <small className="text-muted">
                    <i className="fas fa-exclamation-triangle"></i> {extractionStatus.stale_reason}
                  </small>
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={4}>
          <Card className="h-100">
            <Card.Body>
              <Card.Title className="text-center">
                <i className="fas fa-exclamation-triangle text-warning"></i> Alerts
              </Card.Title>
              <div className="text-center">
                <div className="display-6 mb-2">
                  <Badge bg={recentErrors.length > 0 ? 'danger' : 'success'}>
                    {recentErrors.length}
                  </Badge>
                </div>
                <p className="mb-0">
                  <strong>Recent Errors</strong>
                </p>
                {recentErrors.length > 0 && (
                  <small className="text-muted">
                    Last: {formatTimestamp(recentErrors[0].timestamp)}
                  </small>
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>


      {/* Circuit Breaker Status */}
      <Row className="mb-4">
        <Col>
          <Card>
            <Card.Body>
              <Card.Title>🛡️ Circuit Breaker Status</Card.Title>
              {Object.keys(circuitBreakers).length > 0 ? (
                <Row>
                  {Object.entries(circuitBreakers).map(([name, status]) => (
                    <Col md={4} key={name} className="mb-3">
                      <Card className="h-100">
                        <Card.Body>
                          <div className="d-flex justify-content-between align-items-center mb-2">
                            <h6 className="mb-0">{name}</h6>
                            <Badge bg={getCircuitBreakerBadge(status.state)}>
                              {status.state}
                            </Badge>
                          </div>
                          <small className="text-muted">
                            <div>Requests: {status.total_requests}</div>
                            <div>Success Rate: {formatDecimal(status.success_rate)}%</div>
                            <div>Failures: {status.total_failures}</div>
                            {status.total_blocked > 0 && (
                              <div className="text-warning">Blocked: {status.total_blocked}</div>
                            )}
                          </small>
                        </Card.Body>
                      </Card>
                    </Col>
                  ))}
                </Row>
              ) : (
                <p className="text-muted">
                  <i className="fas fa-clock"></i> No circuit breaker data available
                  <br />
                  <small>Data will appear when extraction processes are running</small>
                </p>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Recent Errors */}
      {recentErrors.length > 0 && (
        <Row className="mb-4">
          <Col>
            <Card>
              <Card.Body>
                <Card.Title>🚨 Recent Errors</Card.Title>
                <div className="error-log" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  {recentErrors.map((error, index) => (
                    <Alert key={index} variant="danger" className="mb-2 py-2">
                      <div className="d-flex justify-content-between">
                        <strong>{error.type || 'Error'}</strong>
                        <small>{formatTimestamp(error.timestamp)}</small>
                      </div>
                      <small>{error.message}</small>
                      {error.diocese && <div><small><strong>Diocese:</strong> {error.diocese}</small></div>}
                    </Alert>
                  ))}
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}

      {/* Recent Extractions History */}
      <Row className="mb-4">
        <Col>
          <Card>
            <Card.Body>
              <Card.Title>📝 Recent Extraction History</Card.Title>
              {extractionHistory.length > 0 ? (
                <Table striped bordered hover responsive>
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Diocese</th>
                      <th>Parishes</th>
                      <th>Success Rate</th>
                      <th>Duration</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {extractionHistory.slice(0, 10).map((extraction, index) => (
                      <tr key={index}>
                        <td>{formatTimestamp(extraction.timestamp)}</td>
                        <td>{extraction.diocese_name}</td>
                        <td>{extraction.parishes_extracted}</td>
                        <td>
                          <Badge bg={extraction.success_rate >= 90 ? 'success' : extraction.success_rate >= 70 ? 'warning' : 'danger'}>
                            {formatDecimal(extraction.success_rate)}%
                          </Badge>
                        </td>
                        <td>{formatDuration(extraction.duration)}</td>
                        <td>
                          <Badge bg={extraction.status === 'completed' ? 'success' : 'danger'}>
                            {extraction.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              ) : (
                <p className="text-muted">No extraction history available</p>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Live Log */}
      <Row>
        <Col>
          <Card>
            <Card.Body>
              <Card.Title>📋 Live Extraction Log</Card.Title>
              <div
                className="live-log bg-dark text-light p-3 rounded text-start"
                style={{
                  height: '400px',
                  overflowY: 'auto',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  textAlign: 'left'
                }}
              >
                <style>
                  {`
                    .live-log a {
                      color: #60a5fa !important;
                      text-decoration: underline;
                    }
                    .live-log a:hover {
                      color: #93c5fd !important;
                      text-decoration: none;
                    }
                  `}
                </style>
                {liveLog.length > 0 ? (
                  liveLog.map((log, index) => (
                    <div key={log.id || index} className="mb-1 d-flex align-items-start text-start">
                      <span className="text-secondary me-2" style={{ minWidth: '140px', fontSize: '0.75rem', textAlign: 'left' }}>
                        [{formatTimestamp(log.timestamp)}]
                      </span>
                      <div className={`flex-grow-1 text-start ${
                        log.level === 'ERROR' ? 'text-danger' :
                        log.level === 'WARNING' ? 'text-warning' :
                        log.level === 'INFO' ? 'text-info' :
                        'text-light'
                      }`}>
                        <span
                          dangerouslySetInnerHTML={{ __html: log.message }}
                          style={{
                            wordBreak: 'break-word',
                            textAlign: 'left',
                            display: 'block'
                          }}
                        />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-muted text-start">No log entries available</div>
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Dashboard;