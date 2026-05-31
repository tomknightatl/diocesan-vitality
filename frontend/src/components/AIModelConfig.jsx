import React, { useState, useEffect } from 'react';
import {
  Container,
  Card,
  Row,
  Col,
  Button,
  Form,
  Badge,
  Alert,
  Spinner,
  OverlayTrigger,
  Tooltip,
} from 'react-bootstrap';
import '../AIComponents.css';

const AIModelConfig = () => {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [config, setConfig] = useState({
    temperature: 0.7,
    max_tokens: 2000,
    top_p: 0.9,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Fetch available models and current configuration
  useEffect(() => {
    fetchModels();
    fetchCurrentConfig();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/ai/models');
      if (!response.ok) {
        throw new Error('Failed to fetch models');
      }
      const data = await response.json();
      setModels(data.models || []);
      if (data.models && data.models.length > 0) {
        setSelectedModel(data.models[0].id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrentConfig = async () => {
    try {
      const response = await fetch('/api/ai/config');
      if (!response.ok) {
        throw new Error('Failed to fetch current configuration');
      }
      const data = await response.json();
      if (data.config) {
        setConfig(data.config);
        if (data.config.model_id) {
          setSelectedModel(data.config.model_id);
        }
      }
    } catch (err) {
      console.error('Error fetching config:', err);
      // Don't set error here as config might not exist yet
    }
  };

  const handleModelSelect = (modelId) => {
    setSelectedModel(modelId);
  };

  const handleConfigChange = (field, value) => {
    setConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const payload = {
        ...config,
        model_id: selectedModel,
      };

      const response = await fetch('/api/ai/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Failed to save configuration');
      }

      setSuccess('Configuration saved successfully!');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const getModelSpecs = (model) => {
    const specs = {
      speed: model.speed || 'medium',
      cost: model.cost || 'medium',
      capability: model.capability || 'general',
      max_tokens: model.max_tokens || 4096,
    };

    const speedColors = {
      fast: 'success',
      medium: 'warning',
      slow: 'danger',
    };

    const costColors = {
      low: 'success',
      medium: 'warning',
      high: 'danger',
    };

    const capabilityColors = {
      general: 'primary',
      advanced: 'info',
      specialized: 'secondary',
    };

    return {
      ...specs,
      speedColor: speedColors[specs.speed] || 'secondary',
      costColor: costColors[specs.cost] || 'secondary',
      capabilityColor: capabilityColors[specs.capability] || 'secondary',
    };
  };

  const getSelectedModel = () => {
    return models.find((m) => m.id === selectedModel);
  };

  if (loading) {
    return (
      <Container className="mt-4">
        <div className="text-center">
          <Spinner animation="border" />
          <p className="mt-2">Loading AI models...</p>
        </div>
      </Container>
    );
  }

  const selectedModelData = getSelectedModel();

  return (
    <Container fluid className="ai-model-config mt-4">
      <Row className="mb-4">
        <Col>
          <h2>🤖 AI Model Configuration</h2>
          <p className="text-muted">
            Configure AI models for data extraction and analysis
          </p>
        </Col>
      </Row>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert variant="success" dismissible onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Model Selection */}
      <Row className="mb-4">
        <Col>
          <Card>
            <Card.Body>
              <Card.Title>🎯 Select AI Model</Card.Title>
              <p className="text-muted mb-3">
                Choose the AI model that best fits your needs
              </p>

              <Row>
                {models.map((model) => {
                  const specs = getModelSpecs(model);
                  const isSelected = selectedModel === model.id;

                  return (
                    <Col md={4} key={model.id} className="mb-3">
                      <Card
                        className={`model-card h-100 cursor-pointer ${
                          isSelected ? 'border-primary bg-primary-subtle' : ''
                        }`}
                        onClick={() => handleModelSelect(model.id)}
                        style={{
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                        }}
                      >
                        <Card.Body>
                          <div className="d-flex justify-content-between align-items-start mb-2">
                            <h5 className="mb-0">{model.name}</h5>
                            {isSelected && (
                              <Badge bg="primary">Selected</Badge>
                            )}
                          </div>
                          <p className="text-muted small mb-3">
                            {model.description || 'General purpose AI model'}
                          </p>

                          <div className="model-specs">
                            <div className="mb-2">
                              <small className="text-muted">Speed:</small>{' '}
                              <Badge bg={specs.speedColor}>{specs.speed}</Badge>
                            </div>
                            <div className="mb-2">
                              <small className="text-muted">Cost:</small>{' '}
                              <Badge bg={specs.costColor}>{specs.cost}</Badge>
                            </div>
                            <div className="mb-2">
                              <small className="text-muted">Capability:</small>{' '}
                              <Badge bg={specs.capabilityColor}>
                                {specs.capability}
                              </Badge>
                            </div>
                            <div>
                              <small className="text-muted">
                                Max Tokens:
                              </small>{' '}
                              <span className="fw-bold">
                                {specs.max_tokens.toLocaleString()}
                              </span>
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Configuration Parameters */}
      {selectedModelData && (
        <Row className="mb-4">
          <Col>
            <Card>
              <Card.Body>
                <Card.Title>⚙️ Model Parameters</Card.Title>
                <p className="text-muted mb-4">
                  Fine-tune the AI model behavior for optimal results
                </p>

                <Row>
                  {/* Temperature */}
                  <Col md={6} className="mb-4">
                    <Form.Group>
                      <Form.Label>
                        <OverlayTrigger
                          placement="top"
                          overlay={
                            <Tooltip>
                              Controls randomness: Lower values make output more
                              focused and deterministic, higher values make it
                              more creative and random.
                            </Tooltip>
                          }
                        >
                          <span>
                            Temperature{' '}
                            <span className="text-muted">(0.0 - 2.0)</span>
                          </span>
                        </OverlayTrigger>
                      </Form.Label>
                      <div className="d-flex align-items-center">
                        <Form.Range
                          min="0"
                          max="2"
                          step="0.1"
                          value={config.temperature}
                          onChange={(e) =>
                            handleConfigChange('temperature', parseFloat(e.target.value))
                          }
                          className="flex-grow-1 me-3"
                        />
                        <Badge bg="primary" className="min-width-60">
                          {config.temperature.toFixed(1)}
                        </Badge>
                      </div>
                      <Form.Text className="text-muted">
                        {config.temperature < 0.3 && 'Very focused and deterministic'}
                        {config.temperature >= 0.3 &&
                          config.temperature < 0.7 &&
                          'Balanced creativity and focus'}
                        {config.temperature >= 0.7 && 'More creative and random'}
                      </Form.Text>
                    </Form.Group>
                  </Col>

                  {/* Max Tokens */}
                  <Col md={6} className="mb-4">
                    <Form.Group>
                      <Form.Label>
                        <OverlayTrigger
                          placement="top"
                          overlay={
                            <Tooltip>
                              Maximum number of tokens to generate in the
                              response. Higher values allow longer responses but
                              may increase cost and latency.
                            </Tooltip>
                          }
                        >
                          <span>
                            Max Tokens{' '}
                            <span className="text-muted">
                              (100 - {selectedModelData.max_tokens || 4096})
                            </span>
                          </span>
                        </OverlayTrigger>
                      </Form.Label>
                      <div className="d-flex align-items-center">
                        <Form.Range
                          min="100"
                          max={selectedModelData.max_tokens || 4096}
                          step="100"
                          value={config.max_tokens}
                          onChange={(e) =>
                            handleConfigChange('max_tokens', parseInt(e.target.value))
                          }
                          className="flex-grow-1 me-3"
                        />
                        <Badge bg="primary" className="min-width-60">
                          {config.max_tokens}
                        </Badge>
                      </div>
                      <Form.Text className="text-muted">
                        Response length limit
                      </Form.Text>
                    </Form.Group>
                  </Col>

                  {/* Top P */}
                  <Col md={6} className="mb-4">
                    <Form.Group>
                      <Form.Label>
                        <OverlayTrigger
                          placement="top"
                          overlay={
                            <Tooltip>
                              Controls diversity via nucleus sampling: Only the
                              most probable tokens with total probability mass
                              of top_p are considered.
                            </Tooltip>
                          }
                        >
                          <span>
                            Top P{' '}
                            <span className="text-muted">(0.0 - 1.0)</span>
                          </span>
                        </OverlayTrigger>
                      </Form.Label>
                      <div className="d-flex align-items-center">
                        <Form.Range
                          min="0"
                          max="1"
                          step="0.05"
                          value={config.top_p}
                          onChange={(e) =>
                            handleConfigChange('top_p', parseFloat(e.target.value))
                          }
                          className="flex-grow-1 me-3"
                        />
                        <Badge bg="primary" className="min-width-60">
                          {config.top_p.toFixed(2)}
                        </Badge>
                      </div>
                      <Form.Text className="text-muted">
                        Nucleus sampling threshold
                      </Form.Text>
                    </Form.Group>
                  </Col>

                  {/* Frequency Penalty */}
                  <Col md={6} className="mb-4">
                    <Form.Group>
                      <Form.Label>
                        <OverlayTrigger
                          placement="top"
                          overlay={
                            <Tooltip>
                              Decreases likelihood of repeating the same line
                              verbatim. Higher values make the model more
                              diverse.
                            </Tooltip>
                          }
                        >
                          <span>
                            Frequency Penalty{' '}
                            <span className="text-muted">(0.0 - 2.0)</span>
                          </span>
                        </OverlayTrigger>
                      </Form.Label>
                      <div className="d-flex align-items-center">
                        <Form.Range
                          min="0"
                          max="2"
                          step="0.1"
                          value={config.frequency_penalty}
                          onChange={(e) =>
                            handleConfigChange(
                              'frequency_penalty',
                              parseFloat(e.target.value),
                            )
                          }
                          className="flex-grow-1 me-3"
                        />
                        <Badge bg="primary" className="min-width-60">
                          {config.frequency_penalty.toFixed(1)}
                        </Badge>
                      </div>
                      <Form.Text className="text-muted">
                        Reduces repetition
                      </Form.Text>
                    </Form.Group>
                  </Col>

                  {/* Presence Penalty */}
                  <Col md={6} className="mb-4">
                    <Form.Group>
                      <Form.Label>
                        <OverlayTrigger
                          placement="top"
                          overlay={
                            <Tooltip>
                              Decreases likelihood of talking about topics that
                              have already been mentioned. Higher values make
                              the model explore new topics.
                            </Tooltip>
                          }
                        >
                          <span>
                            Presence Penalty{' '}
                            <span className="text-muted">(0.0 - 2.0)</span>
                          </span>
                        </OverlayTrigger>
                      </Form.Label>
                      <div className="d-flex align-items-center">
                        <Form.Range
                          min="0"
                          max="2"
                          step="0.1"
                          value={config.presence_penalty}
                          onChange={(e) =>
                            handleConfigChange(
                              'presence_penalty',
                              parseFloat(e.target.value),
                            )
                          }
                          className="flex-grow-1 me-3"
                        />
                        <Badge bg="primary" className="min-width-60">
                          {config.presence_penalty.toFixed(1)}
                        </Badge>
                      </div>
                      <Form.Text className="text-muted">
                        Encourages new topics
                      </Form.Text>
                    </Form.Group>
                  </Col>
                </Row>

                {/* Save Button */}
                <div className="d-flex justify-content-end mt-4">
                  <Button
                    variant="primary"
                    onClick={handleSaveConfig}
                    disabled={saving}
                    size="lg"
                  >
                    {saving ? (
                      <>
                        <Spinner animation="border" size="sm" className="me-2" />
                        Saving...
                      </>
                    ) : (
                      <>
                        💾 Save Configuration
                      </>
                    )}
                  </Button>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}

      {/* Current Configuration Summary */}
      {selectedModelData && (
        <Row className="mb-4">
          <Col>
            <Card>
              <Card.Body>
                <Card.Title>📋 Configuration Summary</Card.Title>
                <Table striped bordered hover responsive>
                  <tbody>
                    <tr>
                      <td><strong>Model</strong></td>
                      <td>{selectedModelData.name}</td>
                    </tr>
                    <tr>
                      <td><strong>Temperature</strong></td>
                      <td>{config.temperature.toFixed(1)}</td>
                    </tr>
                    <tr>
                      <td><strong>Max Tokens</strong></td>
                      <td>{config.max_tokens}</td>
                    </tr>
                    <tr>
                      <td><strong>Top P</strong></td>
                      <td>{config.top_p.toFixed(2)}</td>
                    </tr>
                    <tr>
                      <td><strong>Frequency Penalty</strong></td>
                      <td>{config.frequency_penalty.toFixed(1)}</td>
                    </tr>
                    <tr>
                      <td><strong>Presence Penalty</strong></td>
                      <td>{config.presence_penalty.toFixed(1)}</td>
                    </tr>
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
    </Container>
  );
};

export default AIModelConfig;