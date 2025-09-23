# Examples

This directory contains practical examples and usage samples for the Diocesan Vitality system.

## 📚 Available Examples

### 🚀 Quick Start Examples
- **[Basic Pipeline Run](basic_pipeline_run.py)** - Simple pipeline execution
- **[Custom Configuration](custom_configuration.py)** - Configuring extraction parameters
- **[Diocese-Specific Extraction](diocese_extraction.py)** - Extract data for specific diocese

### 📊 Data Analysis Examples
- **[Data Export](data_export.py)** - Export extracted data to various formats
- **[Statistics Generation](statistics_analysis.py)** - Generate reports and statistics
- **[Data Visualization](data_visualization.py)** - Create charts and visualizations

### 🛠️ Development Examples
- **[Custom Extractor](custom_extractor.py)** - Create website-specific extractors
- **[API Integration](api_integration.py)** - Integrate with external APIs
- **[Monitoring Setup](monitoring_setup.py)** - Set up custom monitoring

### 🔧 Administrative Examples
- **[Database Operations](database_operations.py)** - Database management tasks
- **[Backup and Restore](backup_restore.py)** - Data backup procedures
- **[Performance Tuning](performance_tuning.py)** - Optimization techniques

## 🏃 Running Examples

### Prerequisites
```bash
# Ensure you have the development environment set up
make install

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys
```

### Basic Execution
```bash
# Run from project root
python examples/basic_pipeline_run.py

# Or using the CLI
diocesan-vitality quickstart
```

### Custom Parameters
```bash
# Run with custom parameters
python examples/diocese_extraction.py --diocese-id 123

# Export data
python examples/data_export.py --format csv --output results.csv
```

## 📖 Example Categories

### Beginner Examples
Start here if you're new to the system:
1. [Basic Pipeline Run](basic_pipeline_run.py)
2. [Custom Configuration](custom_configuration.py)
3. [Data Export](data_export.py)

### Intermediate Examples
For users familiar with the basics:
1. [Diocese-Specific Extraction](diocese_extraction.py)
2. [Statistics Generation](statistics_analysis.py)
3. [Custom Extractor](custom_extractor.py)

### Advanced Examples
For power users and developers:
1. [API Integration](api_integration.py)
2. [Performance Tuning](performance_tuning.py)
3. [Monitoring Setup](monitoring_setup.py)

## 🔗 Related Documentation

- **[Local Development Guide](../docs/LOCAL_DEVELOPMENT.md)** - Complete setup instructions
- **[API Documentation](../docs/ARCHITECTURE.md)** - System architecture details
- **[Release Guide](../docs/RELEASE_AUTOMATION_GUIDE.md)** - How to contribute changes

## 💡 Tips for Using Examples

### Modifying Examples
1. Copy the example to a new file
2. Modify parameters as needed
3. Test in development environment first
4. Document your changes

### Error Handling
Examples include basic error handling, but for production use:
- Add comprehensive logging
- Implement retry mechanisms
- Include monitoring and alerting

### Performance Considerations
- Start with small data sets
- Monitor resource usage
- Scale gradually based on results

## 🆘 Support

If you encounter issues with examples:
1. Check the [troubleshooting guide](../docs/LOCAL_DEVELOPMENT.md#troubleshooting)
2. Review [recent issues](https://github.com/tomknightatl/diocesan-vitality/issues)
3. Create a new issue with example code and error details

## 🤝 Contributing Examples

We welcome contributions of new examples! See [Contributing Guide](../CONTRIBUTING.md) for:
- Example coding standards
- Documentation requirements
- Testing procedures
- Submission process
