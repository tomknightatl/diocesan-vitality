# Deployment Checklist - Intelligent Model Routing System

## Pre-Deployment Checklist

### 1. Environment Setup
- [ ] Copy `.env.example` to `.env`
- [ ] Add `GEMINI_API_KEY` to `.env` file
- [ ] Verify `SUPABASE_URL` and `SUPABASE_KEY` are set
- [ ] Ensure Python 3.8+ is installed

### 2. Dependencies Installation
- [ ] Run `pip install -r requirements.txt`
- [ ] Verify all packages installed successfully
- [ ] Test imports: `python3 -c "from ai.model_router import get_router"`

### 3. Configuration
- [ ] Review `config/ai_config.json`
- [ ] Adjust `default_model` if needed
- [ ] Configure `max_retries` and `timeout` values
- [ ] Verify `complexity_calculation` factors
- [ ] Ensure `enable_cost_tracking` is set appropriately

### 4. Testing
- [ ] Run verification script: `python3 verify_implementation.py`
- [ ] All 8 verification tests should pass
- [ ] Start development server: `uvicorn main:app --reload`
- [ ] Test GET `/api/ai/models` endpoint
- [ ] Test POST `/api/ai/generate` endpoint
- [ ] Test GET `/api/ai/costs/summary` endpoint

### 5. Integration Testing
- [ ] Test with actual GEMINI_API_KEY
- [ ] Verify model routing works correctly
- [ ] Check cost tracking functionality
- [ ] Test configuration reload
- [ ] Verify error handling

## Production Deployment

### 1. Security
- [ ] Ensure `.env` file is not committed to Git
- [ ] Set proper file permissions: `chmod 600 .env`
- [ ] Use environment variables in production
- [ ] Enable HTTPS/TLS for API endpoints
- [ ] Implement rate limiting
- [ ] Set up API key rotation

### 2. Monitoring
- [ ] Set up logging for AI requests
- [ ] Monitor cost tracking metrics
- [ ] Set up alerts for high costs
- [ ] Track API error rates
- [ ] Monitor generation times
- [ ] Set up health checks

### 3. Performance
- [ ] Configure connection pooling
- [ ] Set appropriate timeout values
- [ ] Enable caching if needed
- [ ] Optimize database queries
- [ ] Load test the endpoints
- [ ] Monitor resource usage

### 4. Backup and Recovery
- [ ] Backup configuration files
- [ ] Document configuration changes
- [ ] Set up cost tracking backup
- [ ] Create rollback plan
- [ ] Test recovery procedures

## Post-Deployment

### 1. Verification
- [ ] Verify all endpoints are accessible
- [ ] Test model routing with various complexities
- [ ] Check cost tracking accuracy
- [ ] Verify configuration reload works
- [ ] Test error handling

### 2. Documentation
- [ ] Update API documentation
- [ ] Document any custom configurations
- [ ] Create runbook for common issues
- [ ] Document monitoring setup
- [ ] Update team on new features

### 3. Maintenance
- [ ] Schedule regular cost reviews
- [ ] Monitor model performance
- [ ] Update complexity factors if needed
- [ ] Review and update models periodically
- [ ] Keep dependencies updated

## Troubleshooting

### Common Issues

**Issue**: "GEMINI_API_KEY not configured"
- Solution: Add GEMINI_API_KEY to .env file

**Issue**: High costs
- Solution: Review complexity scores, adjust factors, check model selection

**Issue**: Slow generation times
- Solution: Check network, verify timeout settings, consider faster models

**Issue**: Import errors
- Solution: Verify dependencies installed, check Python path

**Issue**: Configuration not loading
- Solution: Check config file path, verify JSON syntax, use reload endpoint

## Support Resources

- Full Documentation: `ai/README.md`
- Implementation Details: `IMPLEMENTATION_SUMMARY.md`
- Quick Reference: `QUICK_REFERENCE.md`
- Verification Script: `verify_implementation.py`
- Test Suite: `tests/test_model_router.py`

## Contact

For issues or questions, refer to the documentation or contact the development team.
