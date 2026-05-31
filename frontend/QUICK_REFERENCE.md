# AI Configuration Components - Quick Reference

## Quick Start

### Access the AI Configuration Page
Navigate to: `http://localhost:5173/ai-config`

### Main Navigation
Click "AI Config" in the main navigation bar

## Component Overview

### 1. Model Configuration Tab
**Purpose:** Configure AI models and parameters

**Key Features:**
- Select AI model from visual cards
- Adjust parameters with sliders:
  - Temperature (0.0 - 2.0)
  - Max Tokens (100 - model limit)
  - Top P (0.0 - 1.0)
  - Frequency Penalty (0.0 - 2.0)
  - Presence Penalty (0.0 - 2.0)
- Save configuration
- View configuration summary

**Best Practices:**
- Start with temperature 0.3-0.5 for focused results
- Use higher temperature (0.7-1.0) for creative tasks
- Monitor quality dashboard after changes
- Save working configurations

### 2. Quality Dashboard Tab
**Purpose:** Monitor AI performance in real-time

**Key Metrics:**
- **Accuracy:** Overall prediction accuracy
- **Confidence:** Average confidence score
- **Improvement Rate:** Quality improvement over time
- **Success Rate:** Percentage of successful extractions

**Detailed Metrics:**
- Precision, Recall, F1 Score
- Response Time
- Error Rate
- Token Efficiency

**Features:**
- Real-time WebSocket updates
- Historical data table
- Recent evaluations table
- AI insights with severity levels
- Session averages

### 3. Information Tab
**Purpose:** Learn about AI configuration and best practices

**Contents:**
- Component descriptions
- Parameter explanations
- Best practices guide
- Troubleshooting tips
- Additional resources

## API Endpoints Reference

### Model Configuration
```
GET    /api/ai/models          # Get available models
GET    /api/ai/config          # Get current configuration
POST   /api/ai/config          # Save configuration
```

### Quality Monitoring
```
GET    /api/ai/quality/metrics       # Get current metrics
GET    /api/ai/quality/history       # Get historical data
GET    /api/ai/quality/insights      # Get AI insights
GET    /api/ai/quality/evaluations   # Get recent evaluations
```

### WebSocket
```
WS     /ws/ai-quality          # Real-time quality updates
```

## File Locations

```
frontend/src/
├── components/
│   ├── AIModelConfig.jsx          # Model configuration component
│   └── AIQualityDashboard.jsx     # Quality dashboard component
├── AIConfiguration.jsx            # Main configuration page
├── AIComponents.css               # Custom styles
├── main.jsx                       # Routing configuration
└── Layout.jsx                     # Navigation bar
```

## Common Tasks

### Change AI Model
1. Go to AI Config page
2. Click on Model Configuration tab
3. Select desired model card
4. Adjust parameters if needed
5. Click "Save Configuration"

### Monitor AI Performance
1. Go to AI Config page
2. Click on Quality Dashboard tab
3. View real-time metrics
4. Check insights for recommendations
5. Review historical data trends

### Troubleshoot Connection Issues
1. Check WebSocket connection status (green = connected)
2. Verify backend API is running
3. Check browser console for errors
4. Refresh the page
5. Check network connectivity

## Parameter Quick Guide

### Temperature
- **0.0 - 0.3:** Very focused, deterministic
- **0.3 - 0.7:** Balanced creativity and focus
- **0.7 - 1.0:** More creative and random
- **1.0 - 2.0:** Highly creative and unpredictable

### Max Tokens
- **100 - 500:** Short responses
- **500 - 1000:** Medium responses
- **1000 - 2000:** Long responses
- **2000+:** Very long responses

### Top P
- **0.9 - 1.0:** Standard nucleus sampling
- **0.7 - 0.9:** More focused sampling
- **0.5 - 0.7:** Very focused sampling

### Frequency Penalty
- **0.0 - 0.5:** Minimal repetition reduction
- **0.5 - 1.0:** Moderate repetition reduction
- **1.0 - 2.0:** Strong repetition reduction

### Presence Penalty
- **0.0 - 0.5:** Minimal topic diversity
- **0.5 - 1.0:** Moderate topic diversity
- **1.0 - 2.0:** High topic diversity

## Color Coding

### Quality Indicators
- 🟢 **Green (90%+):** Excellent
- 🔵 **Blue (75-89%):** Good
- 🟡 **Yellow (60-74%):** Fair
- 🔴 **Red (<60%):** Poor

### Insight Severity
- **Info:** General information
- **Warning:** Caution needed
- **Error:** Action required
- **Success:** Positive outcome

### Model Specifications
- **Speed:** Fast (green), Medium (yellow), Slow (red)
- **Cost:** Low (green), Medium (yellow), High (red)
- **Capability:** General (primary), Advanced (info), Specialized (secondary)

## Keyboard Shortcuts

### Navigation
- `Tab` - Navigate between form fields
- `Shift + Tab` - Navigate backwards
- `Enter` - Submit forms (where applicable)
- `Escape` - Close modals/alerts (where applicable)

## Browser Compatibility

### Supported Browsers
- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

### Required Features
- JavaScript ES6+
- WebSocket support
- CSS Grid and Flexbox
- Local Storage (optional)

## Performance Tips

### For Better Performance
1. Use appropriate max tokens limit
2. Monitor response times
3. Adjust temperature based on task complexity
4. Review quality metrics regularly
5. Act on AI insights promptly

### For Cost Optimization
1. Use faster models for simple tasks
2. Limit max tokens when possible
3. Monitor token efficiency
4. Use appropriate temperature settings
5. Review cost metrics regularly

## Support Resources

### Documentation
- `AI_COMPONENTS_README.md` - Comprehensive documentation
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- Information tab in UI - User guide

### Troubleshooting
1. Check browser console for errors
2. Verify backend API is running
3. Check WebSocket connection status
4. Review network tab in DevTools
5. Contact development team

## Development

### Running Locally
```bash
cd frontend
npm install
npm run dev
```

### Building for Production
```bash
cd frontend
npm run build
```

### File Structure
```
AIModelConfig.jsx (565 lines)
├── Model selection
├── Parameter sliders
├── Save functionality
└── Configuration summary

AIQualityDashboard.jsx (698 lines)
├── WebSocket connection
├── Quality metrics display
├── Performance metrics
├── AI insights
└── Historical data

AIConfiguration.jsx (276 lines)
├── Tab navigation
├── Quick stats
├── Component integration
└── Information tab
```

## Quick Commands

### Check Component Status
```bash
# List AI component files
ls -la frontend/src/components/AI*.jsx

# Check routing
grep "ai-config" frontend/src/main.jsx

# Check navigation
grep "AI Config" frontend/src/Layout.jsx
```

### Verify Implementation
```bash
# Check exports
grep "export default" frontend/src/components/AI*.jsx

# Check imports
grep "import.*AI" frontend/src/main.jsx

# Check CSS
ls -la frontend/src/AI*.css
```

## Status Indicators

### Connection Status
- 🟢 **Connected:** WebSocket active, receiving updates
- 🔴 **Disconnected:** WebSocket inactive, attempting reconnect
- ⚪ **Loading:** Establishing connection

### Loading States
- Spinner: Data loading
- Button disabled: Operation in progress
- Grayed out: Feature not available

### Error States
- Red alert: Error occurred
- Dismissible: Can be closed
- Auto-dismiss: Success messages

## Tips and Tricks

### Model Selection
- Compare speed, cost, and capability
- Consider task requirements
- Check max tokens limit
- Review model descriptions

### Parameter Tuning
- Make small adjustments
- Monitor impact on quality
- Save working configurations
- Document successful settings

### Quality Monitoring
- Check dashboard regularly
- Review trends over time
- Act on insights promptly
- Compare session averages

### Performance Optimization
- Balance quality and speed
- Monitor response times
- Adjust parameters based on metrics
- Use appropriate models for tasks

## Common Issues

### Models Not Loading
- Check backend API
- Verify network connection
- Check browser console
- Refresh page

### Configuration Not Saving
- Verify API endpoint
- Check request format
- Review server logs
- Check permissions

### Dashboard Not Updating
- Check WebSocket connection
- Verify backend WebSocket server
- Check firewall settings
- Refresh page

### Styling Issues
- Clear browser cache
- Check CSS imports
- Verify Bootstrap loaded
- Check browser compatibility

## Success Metrics

### Configuration Success
- ✅ Model selected
- ✅ Parameters adjusted
- ✅ Configuration saved
- ✅ Success message displayed

### Quality Monitoring Success
- ✅ WebSocket connected
- ✅ Metrics updating
- ✅ Insights displayed
- ✅ Historical data available

### User Experience Success
- ✅ Intuitive navigation
- ✅ Clear feedback
- ✅ Responsive design
- ✅ Helpful documentation

---

**Last Updated:** May 30, 2026
**Version:** 1.0.0
**Status:** ✅ Production Ready