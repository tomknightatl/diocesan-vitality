import React, { useState } from 'react';
import { Container, Tabs, Tab, Nav, Card, Row, Col, Badge } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import AIModelConfig from './components/AIModelConfig';
import AIQualityDashboard from './components/AIQualityDashboard';
import './AIComponents.css';

const AIConfiguration = () => {
  const [activeTab, setActiveTab] = useState('config');

  return (
    <Container fluid className="ai-configuration mt-4">
      {/* Header */}
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h1>🤖 AI Configuration & Monitoring</h1>
              <p className="text-muted mb-0">
                Configure AI models and monitor real-time quality metrics
              </p>
            </div>
            <div>
              <Link to="/" className="btn btn-outline-secondary me-2">
                ← Back to Dioceses
              </Link>
            </div>
          </div>
        </Col>
      </Row>

      {/* Quick Stats */}
      <Row className="mb-4">
        <Col md={4}>
          <Card className="h-100">
            <Card.Body>
              <div className="d-flex align-items-center">
                <div className="me-3">
                  <div className="display-6">⚙️</div>
                </div>
                <div>
                  <h6 className="mb-0">Model Configuration</h6>
                  <p className="text-muted small mb-0">
                    Configure AI models and parameters
                  </p>
                </div>
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={4}>
          <Card className="h-100">
            <Card.Body>
              <div className="d-flex align-items-center">
                <div className="me-3">
                  <div className="display-6">📊</div>
                </div>
                <div>
                  <h6 className="mb-0">Quality Monitoring</h6>
                  <p className="text-muted small mb-0">
                    Real-time AI quality metrics
                  </p>
                </div>
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={4}>
          <Card className="h-100">
            <Card.Body>
              <div className="d-flex align-items-center">
                <div className="me-3">
                  <div className="display-6">💡</div>
                </div>
                <div>
                  <h6 className="mb-0">AI Insights</h6>
                  <p className="text-muted small mb-0">
                    Performance insights and recommendations
                  </p>
                </div>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Main Content Tabs */}
      <Card>
        <Card.Body>
          <Tabs
            activeKey={activeTab}
            onSelect={(k) => setActiveTab(k)}
            className="mb-4"
          >
            <Tab eventKey="config" title="⚙️ Model Configuration">
              <AIModelConfig />
            </Tab>

            <Tab eventKey="quality" title="📊 Quality Dashboard">
              <AIQualityDashboard />
            </Tab>

            <Tab eventKey="info" title="ℹ️ Information">
              <Container fluid>
                <Row className="mb-4">
                  <Col>
                    <h3>About AI Configuration</h3>
                    <p className="text-muted">
                      This interface allows you to configure and monitor the AI
                      models used for data extraction and analysis in the
                      Diocesan Vitality system.
                    </p>
                  </Col>
                </Row>

                <Row className="mb-4">
                  <Col md={6}>
                    <Card>
                      <Card.Body>
                        <Card.Title>🎯 Model Configuration</Card.Title>
                        <p>
                          Configure AI models with the following parameters:
                        </p>
                        <ul>
                          <li>
                            <strong>Model Selection:</strong> Choose from
                            available AI models with different capabilities,
                            speeds, and costs
                          </li>
                          <li>
                            <strong>Temperature:</strong> Controls randomness in
                            AI responses (0.0 - 2.0)
                          </li>
                          <li>
                            <strong>Max Tokens:</strong> Maximum response length
                          </li>
                          <li>
                            <strong>Top P:</strong> Nucleus sampling threshold
                          </li>
                          <li>
                            <strong>Frequency Penalty:</strong> Reduces repetition
                          </li>
                          <li>
                            <strong>Presence Penalty:</strong> Encourages new
                            topics
                          </li>
                        </ul>
                      </Card.Body>
                    </Card>
                  </Col>

                  <Col md={6}>
                    <Card>
                      <Card.Body>
                        <Card.Title>📊 Quality Monitoring</CardTitle>
                        <p>
                          Monitor real-time AI performance metrics:
                        </p>
                        <ul>
                          <li>
                            <strong>Accuracy:</strong> Overall prediction accuracy
                          </li>
                          <li>
                            <strong>Confidence:</strong> Average confidence score
                          </li>
                          <li>
                            <strong>Improvement Rate:</strong> Quality improvement
                            over time
                          </li>
                          <li>
                            <strong>Success Rate:</strong> Percentage of successful
                            extractions
                          </li>
                          <li>
                            <strong>Response Time:</strong> Average processing time
                          </li>
                          <li>
                            <strong>Error Rate:</strong> Percentage of failed
                            requests
                          </li>
                        </ul>
                      </Card.Body>
                    </Card>
                  </Col>
                </Row>

                <Row className="mb-4">
                  <Col md={6}>
                    <Card>
                      <Card.Body>
                        <Card.Title>💡 AI Insights</CardTitle>
                        <p>
                          Get actionable insights about AI performance:
                        </p>
                        <ul>
                          <li>
                            <strong>Performance Trends:</strong> Identify
                            improving or degrading performance
                          </li>
                          <li>
                            <strong>Optimization Suggestions:</strong>
                            Recommendations for better configuration
                          </li>
                          <li>
                            <strong>Anomaly Detection:</strong> Alerts for unusual
                            behavior
                          </li>
                          <li>
                            <strong>Model Recommendations:</strong> Suggestions for
                            model selection based on use cases
                          </li>
                        </ul>
                      </Card.Body>
                    </Card>
                  </Col>

                  <Col md={6}>
                    <Card>
                      <Card.Body>
                        <Card.Title>🔧 Best Practices</Card.Title>
                        <p>
                          Tips for optimal AI configuration:
                        </p>
                        <ul>
                          <li>
                            <strong>Start Conservative:</strong> Begin with lower
                            temperature and adjust based on results
                          </li>
                          <li>
                            <strong>Monitor Quality:</strong> Regularly check the
                            quality dashboard for performance trends
                          </li>
                          <li>
                            <strong>Balance Cost & Quality:</strong> Consider both
                            accuracy and cost when selecting models
                          </li>
                          <li>
                            <strong>Test Changes:</strong> Make small adjustments
                            and monitor impact before major changes
                          </li>
                          <li>
                            <strong>Review Insights:</strong> Act on AI insights to
                            continuously improve performance
                          </li>
                        </ul>
                      </Card.Body>
                    </Card>
                  </Col>
                </Row>

                <Row>
                  <Col>
                    <Card bg="light">
                      <Card.Body>
                        <Card.Title>📚 Additional Resources</CardTitle>
                        <p className="mb-0">
                          For more information about AI configuration and best
                          practices, refer to the system documentation or contact
                          the development team.
                        </p>
                      </Card.Body>
                    </Card>
                  </Col>
                </Row>
              </Container>
            </Tab>
          </Tabs>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default AIConfiguration;