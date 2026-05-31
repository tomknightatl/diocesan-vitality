import React, { useState, useEffect, useRef } from 'react';
import {
  Container,
  Card,
  Row,
  Col,
  Badge,
  Alert,
  Spinner,
  Table,
  ProgressBar,
  OverlayTrigger,
  Tooltip,
} from 'react-bootstrap';
import '../AIComponents.css';

const AIQualityDashboard = () => {
  const [connected, setConnected] = useState(false);
  const [qualityMetrics, setQualityMetrics] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [insights, setInsights] = useState([]);
  const [recentEvaluations, setRecentEvaluations] = useState([]);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const maxHistoricalPoints = 50;

  // WebSocket connection for real-time updates
  useEffect(() => {
    connectWebSocket();
    fetchInitialData();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/ai-quality`;

      console.log('🔌 Connecting to AI Quality WebSocket:', wsUrl);

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('✅ AI Quality WebSocket connected');
        setConnected(true);
        setError(null);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      wsRef.current.onclose = () => {
        console.log('❌ AI Quality WebSocket disconnected');
        setConnected(false);

        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.CLOSED) {
            connectWebSocket();
          }
        }, 5000);
      };

      wsRef.current.onerror = (err) => {
        console.error('WebSocket error:', err);
        setError('WebSocket connection error');
      };
    } catch (err) {
      console.error('Error creating WebSocket connection:', err);
      setError('Failed to establish WebSocket connection');
    }
  };

  const fetchInitialData = async () => {
    try {
      // Fetch current quality metrics
      const metricsResponse = await fetch('/api/ai/quality/metrics');
      if (metricsResponse.ok) {
        const data = await metricsResponse.json();
        setQualityMetrics(data.metrics);
      }

      // Fetch historical data
      const historyResponse = await fetch('/api/ai/quality/history');
      if (historyResponse.ok) {
        const data = await historyResponse.json();
        setHistoricalData(data.history || []);
      }

      // Fetch insights
      const insightsResponse = await fetch('/api/ai/quality/insights');
      if (insightsResponse.ok) {
        const data = await insightsResponse.json();
        setInsights(data.insights || []);
      }

      // Fetch recent evaluations
      const evalResponse = await fetch('/api/ai/quality/evaluations');
      if (evalResponse.ok) {
        const data = await evalResponse.json();
        setRecentEvaluations(data.evaluations || []);
      }
    } catch (err) {
      console.error('Error fetching initial data:', err);
      setError('Failed to fetch initial quality data');
    }
  };

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'quality_metrics':
        setQualityMetrics(data.payload);
        // Add to historical data
        setHistoricalData((prev) => {
          const newPoint = {
            timestamp: new Date().toISOString(),
            ...data.payload,
          };
          return [newPoint, ...prev].slice(0, maxHistoricalPoints);
        });
        break;

      case 'quality_insight':
        setInsights((prev) => [data.payload, ...prev].slice(0, 10));
        break;

      case 'evaluation_complete':
        setRecentEvaluations((prev) => [data.payload, ...prev].slice(0, 20));
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const getQualityColor = (value) => {
    if (value >= 90) return 'success';
    if (value >= 75) return 'info';
    if (value >= 60) return 'warning';
    return 'danger';
  };

  const getQualityIcon = (value) => {
    if (value >= 90) return '🟢';
    if (value >= 75) return '🔵';
    if (value >= 60) return '🟡';
    return '🔴';
  };

  const getTrendIcon = (trend) => {
    if (trend > 0) return '📈';
    if (trend < 0) return '📉';
    return '➡️';
  };

  const getTrendColor = (trend) => {
    if (trend > 0) return 'success';
    if (trend < 0) return 'danger';
    return 'secondary';
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatPercentage = (value) => {
    return typeof value === 'number' ? value.toFixed(1) + '%' : 'N/A';
  };

  const calculateAverage = (data, field) => {
    if (!data || data.length === 0) return 0;
    const values = data.map((item) => item[field]).filter((v) => typeof v === 'number');
    if (values.length === 0) return 0;
    return values.reduce((sum, v) => sum + v, 0) / values.length;
  };

  const renderQualityCard = (title, value, trend, icon, description) => {
    const qualityColor = getQualityColor(value);
    const trendColor = getTrendColor(trend);

    return (
      <Card className="h-100">
        <Card.Body>
          <div className="d-flex justify-content-between align-items-start mb-2">
            <div>
              <h6 className="text-muted mb-1">{title}</h6>
              <div className="d-flex align-items-center">
                <span className="display-6 fw-bold me-2">{formatPercentage(value)}</span>
                <Badge bg={qualityColor}>{getQualityIcon(value)}</Badge>
              </div>
            </div>
            <div className="text-end">
              <div className="fs-4">{icon}</div>
              {trend !== 0 && (
                <Badge bg={trendColor} className="mt-1">
                  {getTrendIcon(trend)} {Math.abs(trend).toFixed(1)}%
                </Badge>
              )}
            </div>
          </div>
          <p className="text-muted small mb-0">{description}</p>
        </Card.Body>
      </Card>
    );
  };

  const renderInsightCard = (insight) => {
    const severityColors = {
      info: 'info',
      warning: 'warning',
      error: 'danger',
      success: 'success',
    };

    return (
      <Alert
        variant={severityColors[insight.severity] || 'info'}
        className="mb-2"
        key={insight.id || Math.random()}
      >
        <div className="d-flex justify-content-between align-items-start">
          <div>
            <strong>{insight.title}</strong>
            <p className="mb-0 small">{insight.message}</p>
          </div>
          <small className="text-muted">
            {formatTimestamp(insight.timestamp)}
          </small>
        </div>
      </Alert>
    );
  };

  return (
    <Container fluid className="ai-quality-dashboard mt-4">
      {/* Header */}
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h2>📊 AI Quality Dashboard</h2>
              <p className="text-muted mb-0">
                Real-time monitoring of AI model performance and quality metrics
              </p>
            </div>
            <div className="d-flex align-items-center">
              <Badge bg={connected ? 'success' : 'danger'} className="me-2">
                {connected ? '🟢 Live' : '🔴 Offline'}
              </Badge>
              {!connected && (
                <Spinner animation="border" size="sm" />
              )}
            </div>
          </div>
        </Col>
      </Row>

      {/* Connection Alert */}
      {!connected && (
        <Alert variant="warning" className="mb-4">
          ⚠️ Dashboard disconnected from AI quality monitoring service.
          Attempting to reconnect...
        </Alert>
      )}

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Quality Metrics Cards */}
      <Row className="mb-4">
        <Col md={3}>
          {qualityMetrics ? (
            renderQualityCard(
              'Accuracy',
              qualityMetrics.accuracy || 0,
              qualityMetrics.accuracy_trend || 0,
              '🎯',
              'Overall accuracy of AI predictions',
            )
          ) : (
            <Card className="h-100">
              <Card.Body className="text-center">
                <Spinner animation="border" />
                <p className="mt-2 mb-0">Loading accuracy...</p>
              </Card.Body>
            </Card>
          )}
        </Col>

        <Col md={3}>
          {qualityMetrics ? (
            renderQualityCard(
              'Confidence',
              qualityMetrics.confidence || 0,
              qualityMetrics.confidence_trend || 0,
              '💪',
              'Average confidence score of predictions',
            )
          ) : (
            <Card className="h-100">
              <Card.Body className="text-center">
                <Spinner animation="border" />
                <p className="mt-2 mb-0">Loading confidence...</p>
              </Card.Body>
            </Card>
          )}
        </Col>

        <Col md={3}>
          {qualityMetrics ? (
            renderQualityCard(
              'Improvement Rate',
              qualityMetrics.improvement_rate || 0,
              qualityMetrics.improvement_trend || 0,
              '📈',
              'Rate of quality improvement over time',
            )
          ) : (
            <Card className="h-100">
              <Card.Body className="text-center">
                <Spinner animation="border" />
                <p className="mt-2 mb-0">Loading improvement rate...</p>
              </Card.Body>
            </Card>
          )}
        </Col>

        <Col md={3}>
          {qualityMetrics ? (
            renderQualityCard(
              'Success Rate',
              qualityMetrics.success_rate || 0,
              qualityMetrics.success_trend || 0,
              '✅',
              'Percentage of successful extractions',
            )
          ) : (
            <Card className="h-100">
              <Card.Body className="text-center">
                <Spinner animation="border" />
                <p className="mt-2 mb-0">Loading success rate...</p>
              </Card.Body>
            </Card>
          )}
        </Col>
      </Row>

      {/* Detailed Metrics */}
      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Body>
              <Card.Title>📈 Performance Metrics</Card.Title>
              {qualityMetrics ? (
                <div>
                  <Row className="mb-3">
                    <Col md={6}>
                      <div className="mb-2">
                        <div className="d-flex justify-content-between mb-1">
                          <small>Precision</small>
                          <small className="fw-bold">
                            {formatPercentage(qualityMetrics.precision)}
                          </small>
                        </div>
                        <ProgressBar
                          variant={getQualityColor(qualityMetrics.precision)}
                          now={qualityMetrics.precision}
                        />
                      </div>
                    </Col>
                    <Col md={6}>
                      <div className="mb-2">
                        <div className="d-flex justify-content-between mb-1">
                          <small>Recall</small>
                          <small className="fw-bold">
                            {formatPercentage(qualityMetrics.recall)}
                          </small>
                        </div>
                        <ProgressBar
                          variant={getQualityColor(qualityMetrics.recall)}
                          now={qualityMetrics.recall}
                        />
                      </div>
                    </Col>
                  </Row>

                  <Row className="mb-3">
                    <Col md={6}>
                      <div className="mb-2">
                        <div className="d-flex justify-content-between mb-1">
                          <small>F1 Score</small>
                          <small className="fw-bold">
                            {formatPercentage(qualityMetrics.f1_score)}
                          </small>
                        </div>
                        <ProgressBar
                          variant={getQualityColor(qualityMetrics.f1_score)}
                          now={qualityMetrics.f1_score}
                        />
                      </div>
                    </Col>
                    <Col md={6}>
                      <div className="mb-2">
                        <div className="d-flex justify-content-between mb-1">
                          <small>Response Time</small>
                          <small className="fw-bold">
                            {qualityMetrics.response_time?.toFixed(2) || 'N/A'}s
                          </small>
                        </div>
                        <ProgressBar
                          variant={
                            qualityMetrics.response_time < 2
                              ? 'success'
                              : qualityMetrics.response_time < 5
                                ? 'warning'
                                : 'danger'
                          }
                          now={Math.min((qualityMetrics.response_time || 0) * 20, 100)}
                        />
                      </div>
                    </Col>
                  </Row>

                  <Row>
                    <Col md={6}>
                      <div className="mb-2">
                        <div className="d-flex justify-content-between mb-1">
                          <small>Error Rate</small>
                          <small className="fw-bold">
                            {formatPercentage(qualityMetrics.error_rate)}
                          </small>
                        </div>
                        <ProgressBar
                          variant={
                            qualityMetrics.error_rate < 5
                              ? 'success'
                              : qualityMetrics.error_rate < 10
                                ? 'warning'
                                : 'danger'
                          }
                          now={qualityMetrics.error_rate}
                        />
                      </div>
                    </Col>
                    <Col md={6}>
                      <div className="mb-2">
                        <div className="d-flex justify-content-between mb-1">
                          <small>Token Efficiency</small>
                          <small className="fw-bold">
                            {formatPercentage(qualityMetrics.token_efficiency)}
                          </small>
                        </div>
                        <ProgressBar
                          variant={getQualityColor(qualityMetrics.token_efficiency)}
                          now={qualityMetrics.token_efficiency}
                        />
                      </div>
                    </Col>
                  </Row>
                </div>
              ) : (
                <div className="text-center py-4">
                  <Spinner animation="border" />
                  <p className="mt-2 mb-0">Loading performance metrics...</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col md={6}>
          <Card>
            <Card.Body>
              <Card.Title>💡 AI Insights</Card.Title>
              <div
                style={{
                  maxHeight: '400px',
                  overflowY: 'auto',
                }}
              >
                {insights.length > 0 ? (
                  insights.map((insight) => renderInsightCard(insight))
                ) : (
                  <div className="text-center py-4">
                    <p className="text-muted mb-0">
                      No insights available yet. Insights will appear as the AI
                      processes data.
                    </p>
                  </div>
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Historical Data Table */}
      <Row className="mb-4">
        <Col>
          <Card>
            <Card.Body>
              <Card.Title>📊 Historical Quality Data</Card.Title>
              {historicalData.length > 0 ? (
                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  <Table striped bordered hover responsive size="sm">
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>Accuracy</th>
                        <th>Confidence</th>
                        <th>Success Rate</th>
                        <th>Response Time</th>
                        <th>Error Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historicalData.slice(0, 20).map((data, index) => (
                        <tr key={index}>
                          <td>{formatTimestamp(data.timestamp)}</td>
                          <td>
                            <Badge bg={getQualityColor(data.accuracy)}>
                              {formatPercentage(data.accuracy)}
                            </Badge>
                          </td>
                          <td>
                            <Badge bg={getQualityColor(data.confidence)}>
                              {formatPercentage(data.confidence)}
                            </Badge>
                          </td>
                          <td>
                            <Badge bg={getQualityColor(data.success_rate)}>
                              {formatPercentage(data.success_rate)}
                            </Badge>
                          </td>
                          <td>{data.response_time?.toFixed(2) || 'N/A'}s</td>
                          <td>
                            <Badge
                              bg={
                                data.error_rate < 5
                                  ? 'success'
                                  : data.error_rate < 10
                                    ? 'warning'
                                    : 'danger'
                              }
                            >
                              {formatPercentage(data.error_rate)}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-4">
                  <p className="text-muted mb-0">
                    No historical data available yet. Data will be collected as
                    the AI processes requests.
                  </p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Recent Evaluations */}
      <Row className="mb-4">
        <Col>
          <Card>
            <Card.Body>
              <Card.Title>🔍 Recent Evaluations</Card.Title>
              {recentEvaluations.length > 0 ? (
                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  <Table striped bordered hover responsive size="sm">
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>Task Type</th>
                        <th>Model</th>
                        <th>Accuracy</th>
                        <th>Confidence</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentEvaluations.slice(0, 15).map((eval, index) => (
                        <tr key={index}>
                          <td>{formatTimestamp(eval.timestamp)}</td>
                          <td>{eval.task_type || 'N/A'}</td>
                          <td>{eval.model || 'N/A'}</td>
                          <td>
                            <Badge bg={getQualityColor(eval.accuracy)}>
                              {formatPercentage(eval.accuracy)}
                            </Badge>
                          </td>
                          <td>
                            <Badge bg={getQualityColor(eval.confidence)}>
                              {formatPercentage(eval.confidence)}
                            </Badge>
                          </td>
                          <td>
                            <Badge
                              bg={
                                eval.status === 'success'
                                  ? 'success'
                                  : eval.status === 'partial'
                                    ? 'warning'
                                    : 'danger'
                              }
                            >
                              {eval.status}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-4">
                  <p className="text-muted mb-0">
                    No recent evaluations available. Evaluations will appear as
                    the AI processes tasks.
                  </p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Averages Summary */}
      {historicalData.length > 0 && (
        <Row className="mb-4">
          <Col>
            <Card>
              <Card.Body>
                <Card.Title>📈 Session Averages</Card.Title>
                <Row>
                  <Col md={3}>
                    <div className="text-center">
                      <h5 className="mb-1">
                        {formatPercentage(calculateAverage(historicalData, 'accuracy'))}
                      </h5>
                      <small className="text-muted">Average Accuracy</small>
                    </div>
                  </Col>
                  <Col md={3}>
                    <div className="text-center">
                      <h5 className="mb-1">
                        {formatPercentage(calculateAverage(historicalData, 'confidence'))}
                      </h5>
                      <small className="text-muted">Average Confidence</small>
                    </div>
                  </Col>
                  <Col md={3}>
                    <div className="text-center">
                      <h5 className="mb-1">
                        {formatPercentage(calculateAverage(historicalData, 'success_rate'))}
                      </h5>
                      <small className="text-muted">Average Success Rate</small>
                    </div>
                  </Col>
                  <Col md={3}>
                    <div className="text-center">
                      <h5 className="mb-1">
                        {calculateAverage(historicalData, 'response_time').toFixed(2)}s
                      </h5>
                      <small className="text-muted">Average Response Time</small>
                    </div>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
    </Container>
  );
};

export default AIQualityDashboard;