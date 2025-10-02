# OpenAI Watchdog Development Setup

This document provides instructions for developers working on the OpenAI Watchdog add-on.

## Development Environment Setup

### Prerequisites

- Docker or Home Assistant OS/Supervised environment
- Git
- Text editor/IDE
- OpenAI API key (for testing)

### Local Development

1. **Clone Repository**
   ```bash
   git clone https://github.com/evandepol/hassio-addons.git
   cd hassio-addons
   ```

2. **Switch to Development Branch** (if working on new features)
   ```bash
   git checkout -b openai-watchdog-dev
   ```

### Dependency Management

The OpenAI Watchdog add-on uses the following Python dependencies:

#### Core Dependencies (Dockerfile)
```dockerfile
RUN pip3 install --no-cache-dir \
    openai \           # OpenAI API client
    pyyaml \          # YAML configuration parsing
    schedule \        # Task scheduling
    python-dateutil   # Date/time utilities
```

#### System Dependencies
```dockerfile
RUN apk add --no-cache \
    python3 \         # Python runtime
    py3-pip \         # Package installer
    py3-aiohttp \     # Async HTTP client (pre-installed)
    py3-asyncio \     # Async support (pre-installed)
    bash \            # Shell
    curl \            # HTTP client for testing
    jq                # JSON processing
```

### Adding New Dependencies

1. **Update Dockerfile**
   Add the package to the `pip3 install` command:
   ```dockerfile
   && pip3 install --no-cache-dir \
       openai \
       pyyaml \
       schedule \
       python-dateutil \
       new-package-name \
   ```

2. **Update Import Statement**
   Add proper error handling for new dependencies:
   ```python
   try:
       from new_package import SomeClass
   except ImportError:
       SomeClass = None
       logger.warning("new-package not available")
   ```

3. **Test Installation**
   Build and test the add-on to verify the dependency installs correctly.

## Code Structure

### File Organization
```
openai-watchdog/
├── config.yaml           # Add-on configuration schema
├── build.yaml           # Multi-arch build configuration
├── Dockerfile           # Container definition
├── run.sh              # Entry point script
├── README.md           # User documentation
├── INSTALLATION.md     # Detailed setup guide
├── DEVELOPMENT.md      # This file
└── watchdog/           # Python application
    ├── main.py         # Main application entry
    ├── openai_analyzer.py   # OpenAI API integration
    ├── cost_tracker.py      # Cost management
    ├── ha_client.py         # Home Assistant API client
    ├── insight_manager.py   # Insight processing
    └── watchdog_monitor.py  # Main monitoring loop
```

### Key Components

1. **openai_analyzer.py** - Core OpenAI integration
   - Handles API authentication
   - Manages model selection and pricing
   - Processes state change analysis
   - Implements fallback/mock analysis

2. **cost_tracker.py** - Cost management
   - Tracks daily API usage and costs
   - Implements spending limits
   - Provides cost reporting

3. **ha_client.py** - Home Assistant integration
   - Connects to HA API via Supervisor
   - Fetches state changes
   - Sends notifications

## Testing

### Unit Testing

Create test files for core components:

```python
# tests/test_openai_analyzer.py
import pytest
from unittest.mock import AsyncMock, patch
from watchdog.openai_analyzer import OpenAIAnalyzer

@pytest.mark.asyncio
async def test_analyze_changes_with_mock():
    analyzer = OpenAIAnalyzer(model="gpt-4o-mini")
    # Test with mock data
    changes = [{"entity_id": "sensor.test", "new_state": "on"}]
    result = await analyzer._mock_openai_analysis(changes)
    assert "cost_info" in result
    assert result["processed_changes"] == 1
```

### Integration Testing

1. **Development Mode Testing**
   ```bash
   # Test without API calls (mock mode)
   export OPENAI_API_KEY=""
   ./run.sh
   ```

2. **API Testing with Low Costs**
   ```bash
   # Use gpt-4o-mini for minimal costs
   export OPENAI_API_KEY="sk-your-test-key"
   export OPENAI_MODEL="gpt-4o-mini"
   ./run.sh
   ```

### Build Testing

1. **Local Docker Build**
   ```bash
   cd openai-watchdog
   docker build -t openai-watchdog-test .
   ```

2. **Multi-Architecture Build**
   ```bash
   # Test ARM64 build
   docker buildx build --platform linux/arm64 -t openai-watchdog-arm64 .
   ```

## Development Workflow

### Using Dev Scripts

Use the development scripts in `dev/scripts/` for efficient development:

```bash
# Start file watching for auto-rebuild
./dev/scripts/dev-watch.sh openai-watchdog &

# Build and deploy to test environment
./dev/scripts/dev-build.sh openai-watchdog haos

# Build for all environments
./dev/scripts/dev-build-all.sh openai-watchdog
```

### Configuration During Development

Create a test configuration file:

```yaml
# test-config.yaml
openai_api_key: "sk-test-key-for-development"
openai_model: "gpt-4o-mini"
daily_cost_limit: 0.10
monitoring_scope:
  - climate
analysis_interval: 1  # More frequent for testing
```

### Debugging

1. **Enable Debug Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Mock Mode for Development**
   - Leave `openai_api_key` empty to enable mock analysis
   - Test all functionality without API costs

3. **API Call Monitoring**
   - Monitor `/config/openai-watchdog/costs/` for real-time cost tracking
   - Check `/config/openai-watchdog/logs/` for detailed operation logs

## Version Management

### Development Versions

- Development builds use timestamps: `dev-20250102-143022`
- Never commit development version numbers to `config.yaml`
- Use `.dev-version` files (gitignored) to track current dev builds

### Release Process

1. **Update Version**
   ```yaml
   # config.yaml
   version: "1.1.0"
   ```

2. **Update Changelog**
   Document changes in `CHANGELOG.md`

3. **Test Thoroughly**
   - Test on multiple architectures
   - Verify API integration
   - Check cost calculations

4. **Create Release**
   - Tag the release: `git tag v1.1.0`
   - Push to trigger automated builds

## Common Development Issues

### OpenAI Package Import Errors

**Issue**: `ImportError: No module named 'openai'`

**Solutions**:
1. Verify Dockerfile includes `openai` in pip install
2. Check container build logs for installation errors
3. Ensure Python version compatibility (Python 3.8+)

**Prevention**:
- Always use try/except for imports
- Provide meaningful error messages
- Implement fallback behavior

### API Key Configuration

**Issue**: API key not found or invalid format

**Solutions**:
1. Ensure key starts with `sk-`
2. Check for whitespace or formatting issues
3. Verify environment variable is set correctly

**Prevention**:
- Validate API key format in configuration
- Provide clear error messages
- Document key requirements

### Cost Management

**Issue**: Unexpected high API costs

**Solutions**:
1. Implement daily limits strictly
2. Monitor token usage in real-time
3. Use cheaper models for development

**Prevention**:
- Default to cost-effective models
- Set conservative daily limits
- Provide cost estimates in documentation

## Best Practices

### Code Quality

1. **Error Handling**
   - Always handle API failures gracefully
   - Provide informative error messages
   - Implement fallback behavior

2. **Logging**
   - Use structured logging with appropriate levels
   - Include context in log messages
   - Avoid logging sensitive information

3. **Configuration**
   - Validate all configuration options
   - Provide sensible defaults
   - Document all options clearly

### Security

1. **API Key Management**
   - Never log API keys
   - Use environment variables
   - Validate key format

2. **Data Privacy**
   - Only send necessary data to APIs
   - Avoid personal information
   - Document data usage clearly

### Performance

1. **API Efficiency**
   - Batch requests when possible
   - Implement caching for repeated queries
   - Use appropriate models for the task

2. **Resource Usage**
   - Monitor memory consumption
   - Implement cleanup for old data
   - Use async operations appropriately

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

### Code Review Checklist

- [ ] All dependencies properly declared
- [ ] Error handling implemented
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No API keys or sensitive data in code
- [ ] Follows existing code style
- [ ] Installation process documented

---

For additional help with development, see the main [development documentation](../dev/DEVELOPMENT.md).