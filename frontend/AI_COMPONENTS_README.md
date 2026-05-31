# AI Configuration Components

This directory contains the frontend components for AI model configuration and quality monitoring in the Diocesan Vitality system.

## Components

### 1. AIModelConfig.jsx
**Location:** `frontend/src/components/AIModelConfig.jsx`

**Purpose:** Provides a user interface for configuring AI models used in data extraction and analysis.

**Features:**
- Model selection interface with visual cards for each available model
- Model specifications display (speed, cost, capability, max tokens)
- Configurable parameters:
  - Temperature (0.0 - 2.0): Controls randomness in AI responses
  - Max Tokens (100 - model limit): Maximum response length
  - Top P (0.0 - 1.0): Nucleus sampling threshold
  - Frequency Penalty (0.0 - 2.0): Reduces repetition
  - Presence Penalty (0.0 - 2.0): Encourages new topics
- Save configuration functionality with loading states
- Configuration summary display
- Error handling and success notifications
- Responsive design with Bootstrap styling

**API Endpoints:**
- `GET /api/ai/models` - Fetch available AI models
- `GET /api/ai/config` - Fetch current AI configuration
- `POST /api/ai/config` - Save AI configuration

**Usage Example:**
```jsx
import AIModelConfig from './components/AIModelConfig';

function MyPage() {
  return <AIModelConfig />;
}
```

### 2. AIQualityDashboard.jsx
**Location:** `frontend/src/components/AIQualityDashboard.jsx`

**Purpose:** Real-time monitoring dashboard for AI model performance and quality metrics.

**Features:**
- Real-time WebSocket integration for live updates
- Quality metrics display:
  - Accuracy: Overall prediction accuracy
  - Confidence: Average confidence score
  - Improvement Rate: Quality improvement over time
  - Success Rate: Percentage of successful extractions
- Detailed performance metrics:
  - Precision, Recall, F1 Score
  - Response Time
  - Error Rate
  - Token Efficiency
- AI insights display with severity levels (info, warning, error, success)
- Historical quality data table
- Recent evaluations table
- Session averages calculation
- Visual quality indicators with color-coded badges and progress bars
- Connection status monitoring with auto-reconnection
- Responsive design with scrollable containers

**WebSocket Endpoints:**
- `ws://host/ws/ai-quality` - Real-time quality updates

**API Endpoints:**
- `GET /api/ai/quality/metrics` - Fetch current quality metrics
- `GET /api/ai/quality/history` - Fetch historical quality data
- `GET /api/ai/quality/insights` - Fetch AI insights
- `GET /api/ai/quality/evaluations` - Fetch recent evaluations

**WebSocket Message Types:**
- `quality_metrics` - Real-time quality metrics updates
- `quality_insight` - New AI insights
- `evaluation_complete` - Evaluation completion notifications

**Usage Example:**
```jsx
import AIQualityDashboard from './components/AIQualityDashboard';

function MyPage() {
  return <AIQualityDashboard />;
}
```

### 3. AIConfiguration.jsx
**Location:** `frontend/src/AIConfiguration.jsx`

**Purpose:** Main page that brings together all AI-related components in a tabbed interface.

**Features:**
- Tabbed interface for easy navigation between components
- Quick stats cards showing available features
- Model Configuration tab
- Quality Dashboard tab
- Information tab with:
  - Component descriptions
  - Best practices
  - Additional resources
- Navigation links to other pages
- Responsive design

**Usage Example:**
```jsx
import AIConfiguration from './AIConfiguration';

// In your router configuration
{
  path: "/ai-config",
  element: <AIConfiguration />,
}
```

## Styling

### AIComponents.css
**Location:** `frontend/src/AIComponents.css`

**Purpose:** Custom CSS styles for AI configuration components.

**Features:**
- Model card hover effects and transitions
- Quality card animations
- Responsive design adjustments
- Loading and error state styling
- Custom scrollbar styling
- Progress bar animations
- Connection status pulse animation
- Form range slider customization
- Tooltip improvements

**Key Classes:**
- `.ai-model-config` - Model configuration container
- `.ai-quality-dashboard` - Quality dashboard container
- `.ai-configuration` - Main configuration page container
- `.model-card` - Individual model selection cards
- `.quality-card` - Quality metric cards
- `.insight-card` - AI insight cards
- `.cursor-pointer` - Pointer cursor for interactive elements
- `.min-width-60` - Minimum width for badges

## Routing

The AI configuration page is integrated into the main application routing:

**Location:** `frontend/src/main.jsx`

```jsx
{
  path: "/ai-config",
  element: <AIConfiguration />,
}
```

**Navigation:** Added to the main navigation bar in `frontend/src/Layout.jsx`

## Dependencies

All components use:
- React 19+
- React Bootstrap 5.3+
- React Router DOM 7+

No additional dependencies are required beyond the existing project dependencies.

## API Integration

### Backend Requirements

The frontend components expect the following backend API endpoints:

#### AI Model Configuration
```
GET /api/ai/models
Response: {
  "models": [
    {
      "id": "model-id",
      "name": "Model Name",
      "description": "Model description",
      "speed": "fast|medium|slow",
      "cost": "low|medium|high",
      "capability": "general|advanced|specialized",
      "max_tokens": 4096
    }
  ]
}

GET /api/ai/config
Response: {
  "config": {
    "model_id": "model-id",
    "temperature": 0.7,
    "max_tokens": 2000,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  }
}

POST /api/ai/config
Request: {
  "model_id": "model-id",
  "temperature": 0.7,
  "max_tokens": 2000,
  "top_p": 0.9,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0
}
Response: {
  "success": true,
  "message": "Configuration saved successfully"
}
```

#### AI Quality Monitoring
```
GET /api/ai/quality/metrics
Response: {
  "metrics": {
    "accuracy": 85.5,
    "accuracy_trend": 2.3,
    "confidence": 78.2,
    "confidence_trend": 1.5,
    "improvement_rate": 5.8,
    "improvement_trend": 0.8,
    "success_rate": 92.1,
    "success_trend": 1.2,
    "precision": 87.3,
    "recall": 83.9,
    "f1_score": 85.6,
    "response_time": 1.8,
    "error_rate": 3.2,
    "token_efficiency": 91.5
  }
}

GET /api/ai/quality/history
Response: {
  "history": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "accuracy": 85.5,
      "confidence": 78.2,
      "success_rate": 92.1,
      "response_time": 1.8,
      "error_rate": 3.2
    }
  ]
}

GET /api/ai/quality/insights
Response: {
  "insights": [
    {
      "id": "insight-id",
      "title": "Insight Title",
      "message": "Insight message",
      "severity": "info|warning|error|success",
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ]
}

GET /api/ai/quality/evaluations
Response: {
  "evaluations": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "task_type": "extraction",
      "model": "model-id",
      "accuracy": 85.5,
      "confidence": 78.2,
      "status": "success|partial|failure"
    }
  ]
}
```

#### WebSocket Connection
```
WS /ws/ai-quality

Message Types:
{
  "type": "quality_metrics",
  "payload": {
    "accuracy": 85.5,
    "confidence": 78.2,
    // ... other metrics
  }
}

{
  "type": "quality_insight",
  "payload": {
    "id": "insight-id",
    "title": "Insight Title",
    "message": "Insight message",
    "severity": "info",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}

{
  "type": "evaluation_complete",
  "payload": {
    "timestamp": "2024-01-01T12:00:00Z",
    "task_type": "extraction",
    "model": "model-id",
    "accuracy": 85.5,
    "confidence": 78.2,
    "status": "success"
  }
}
```

## Best Practices

### Model Configuration
1. **Start Conservative**: Begin with lower temperature (0.3-0.5) and adjust based on results
2. **Monitor Quality**: Regularly check the quality dashboard for performance trends
3. **Balance Cost & Quality**: Consider both accuracy and cost when selecting models
4. **Test Changes**: Make small adjustments and monitor impact before major changes
5. **Save Configurations**: Save working configurations for easy rollback

### Quality Monitoring
1. **Regular Monitoring**: Check the dashboard regularly for performance trends
2. **Act on Insights**: Respond to AI insights and recommendations promptly
3. **Track Improvements**: Monitor improvement rates to validate configuration changes
4. **Error Analysis**: Review error rates and investigate patterns
5. **Historical Comparison**: Use historical data to identify long-term trends

### Performance Optimization
1. **WebSocket Connection**: Ensure WebSocket connection is stable for real-time updates
2. **Data Refreshing**: Components automatically refresh data on mount and via WebSocket
3. **Error Handling**: All components include comprehensive error handling
4. **Loading States**: Proper loading indicators improve user experience
5. **Responsive Design**: Components work well on desktop, tablet, and mobile devices

## Troubleshooting

### Common Issues

**Issue: Models not loading**
- Check backend API endpoint `/api/ai/models` is accessible
- Verify network connectivity
- Check browser console for error messages

**Issue: Configuration not saving**
- Verify backend API endpoint `/api/ai/config` accepts POST requests
- Check request payload format matches expected structure
- Review server logs for errors

**Issue: Quality dashboard not updating**
- Verify WebSocket endpoint `/ws/ai-quality` is accessible
- Check WebSocket connection status in browser DevTools
- Ensure backend is sending WebSocket messages

**Issue: WebSocket connection failing**
- Check WebSocket URL protocol (ws:// or wss://)
- Verify firewall settings allow WebSocket connections
- Review backend WebSocket server logs

**Issue: Styling issues**
- Ensure `AIComponents.css` is imported in components
- Check Bootstrap CSS is loaded
- Verify CSS file paths are correct

## Development

### Adding New Features

1. **New Model Parameters**: Add to config state in `AIModelConfig.jsx`
2. **New Quality Metrics**: Add to quality metrics display in `AIQualityDashboard.jsx`
3. **New WebSocket Messages**: Add message handler in `AIQualityDashboard.jsx`
4. **New Tabs**: Add to `AIConfiguration.jsx` tab interface

### Testing

Components should be tested for:
- API integration
- WebSocket connectivity
- Error handling
- Loading states
- Responsive design
- User interactions

### Accessibility

All components follow accessibility best practices:
- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- Color contrast compliance
- Screen reader friendly

## Future Enhancements

Potential improvements:
- Model comparison tool
- A/B testing interface
- Advanced analytics charts
- Export configuration functionality
- Configuration templates
- Model performance predictions
- Cost optimization recommendations
- Automated quality alerts

## Support

For issues or questions:
1. Check this documentation
2. Review browser console for errors
3. Check backend API logs
4. Contact development team

## License

These components are part of the Diocesan Vitality project.