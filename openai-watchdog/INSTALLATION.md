# OpenAI Watchdog Installation Guide

This guide provides step-by-step instructions for installing and configuring the OpenAI Watchdog add-on for Home Assistant.

## Prerequisites

- Home Assistant OS, Supervised, or Core installation
- OpenAI API account and API key
- Internet connection for API calls

## Installation Methods

### Method 1: Quick Installation (Recommended)

1. **Add Repository**
   
   Click the badge below to automatically add this repository to your Home Assistant:
   
   [![Open your Home Assistant instance and show the add add-on repository dialog with this repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fevandepol%2Fhassio-addons)

2. **Install Add-on**
   
   Click the badge below to install the OpenAI Watchdog add-on:
   
   [![Open your Home Assistant instance and show the dashboard of a Supervisor add-on.](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=openai_watchdog&repository_url=https%3A%2F%2Fgithub.com%2Fevandepol%2Fhassio-addons)

### Method 2: Manual Installation

1. **Add Repository**
   - Navigate to **Settings** → **Add-ons** → **Add-on Store**
   - Click the three dots menu (⋮) in the top right corner
   - Select **Repositories**
   - Add the URL: `https://github.com/evandepol/hassio-addons`
   - Click **Add**

2. **Install Add-on**
   - Find "OpenAI Watchdog" in the add-on store
   - Click on it and select **Install**
   - Wait for the installation to complete

## Configuration

### 1. Obtain OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Click **Create new secret key**
5. Copy the generated API key (it starts with `sk-`)
6. **Important**: Store this key securely - you won't be able to see it again

### 2. Configure the Add-on

1. **Open Add-on Configuration**
   - Go to **Settings** → **Add-ons** → **OpenAI Watchdog**
   - Click on the **Configuration** tab

2. **Required Settings**
   ```yaml
   openai_api_key: "sk-your-api-key-here"
   ```

3. **Optional Settings** (with defaults)
   ```yaml
   openai_model: "gpt-4o-mini"  # Options: gpt-4o-mini, gpt-4o, gpt-3.5-turbo
   monitoring_scope:
     - climate
     - security
     - energy
     - automation_performance
   daily_cost_limit: 1.0
   insight_threshold: 0.8
   change_buffer_size: 100
   analysis_interval: 5
   ```

4. **Save Configuration**
   - Click **Save** to apply your settings

### 3. Start the Add-on

1. Click the **Start** button
2. Enable **Start on boot** if desired
3. Check the **Log** tab for startup messages

## Configuration Options Explained

| Option | Description | Default | Required |
|--------|-------------|---------|----------|
| `openai_api_key` | Your OpenAI API key | - | ✅ |
| `openai_model` | OpenAI model to use | `gpt-4o-mini` | ❌ |
| `monitoring_scope` | Areas to monitor | All domains | ❌ |
| `daily_cost_limit` | Maximum daily API cost ($) | `1.0` | ❌ |
| `insight_threshold` | Confidence threshold (0.0-1.0) | `0.8` | ❌ |
| `change_buffer_size` | Number of changes to buffer | `100` | ❌ |
| `analysis_interval` | Analysis frequency (minutes) | `5` | ❌ |

## Model Selection Guide

| Model | Cost | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| `gpt-4o-mini` | Lowest | Fastest | Good | Daily monitoring |
| `gpt-3.5-turbo` | Low | Fast | Good | General use |
| `gpt-4o` | Higher | Slower | Excellent | Critical analysis |

**Recommendation**: Start with `gpt-4o-mini` for cost-effective monitoring.

## Cost Management

### Estimated Daily Costs

- **gpt-4o-mini**: ~$0.10-0.50/day (recommended)
- **gpt-3.5-turbo**: ~$0.25-1.00/day
- **gpt-4o**: ~$1.00-5.00/day

### Cost Control Features

1. **Daily Limits**: Automatically stops when limit reached
2. **Real-time Tracking**: Monitor costs in `/config/openai-watchdog/costs/`
3. **Smart Batching**: Groups changes to reduce API calls
4. **Configurable Intervals**: Adjust analysis frequency

## Verification

### 1. Check Add-on Status

- Green dot indicates running
- Check **Log** tab for any errors

### 2. Verify API Connection

Look for log entries like:
```
[INFO] Initialized OpenAI client with model: gpt-4o-mini
[INFO] OpenAI Watchdog started successfully
```

### 3. Monitor Data Directory

The add-on creates files in `/config/openai-watchdog/`:
- `insights/` - Analysis results
- `costs/` - Daily cost tracking
- `logs/` - Detailed logs

## Troubleshooting

### Common Issues

1. **"No OpenAI API key found"**
   - Ensure `openai_api_key` is set in configuration
   - Verify the key starts with `sk-`
   - Check for extra spaces or quotes

2. **"OpenAI package not installed"**
   - Restart the add-on
   - Check installation logs
   - Try reinstalling the add-on

3. **High API Costs**
   - Reduce `analysis_interval`
   - Lower `daily_cost_limit`
   - Switch to `gpt-4o-mini`
   - Limit `monitoring_scope`

4. **No Insights Generated**
   - Check `insight_threshold` (try 0.5)
   - Verify entities are changing
   - Review log files for errors

### Getting Help

1. **Check Logs**
   - Add-on → Log tab
   - `/config/openai-watchdog/logs/`

2. **Review Configuration**
   - Validate YAML syntax
   - Ensure all required fields are set

3. **Report Issues**
   - [GitHub Issues](https://github.com/evandepol/hassio-addons/issues)
   - Include log excerpts and configuration (redact API key)

## Advanced Configuration

### Custom Monitoring Scope

```yaml
monitoring_scope:
  - climate          # Temperature, HVAC
  - security         # Doors, locks, alarms
  - energy           # Power monitoring
  - automation_performance  # Automation health
  - device_health    # Device status
  - patterns         # Usage patterns
```

### Environment Variables

The add-on automatically sets:
- `OPENAI_API_KEY` - From configuration
- `OPENAI_MODEL` - Selected model
- `OPENAI_WATCHDOG_DATA` - Data directory path

## Security Considerations

1. **API Key Protection**
   - Never share your API key
   - Rotate keys periodically
   - Monitor usage on OpenAI dashboard

2. **Data Privacy**
   - Only entity states are sent to OpenAI
   - No personal information transmitted
   - Local data storage with restricted permissions

3. **Network Security**
   - All API calls use HTTPS
   - No external access to Home Assistant required

## Next Steps

After installation:

1. **Monitor Initial Operation** - Check logs for first 24 hours
2. **Adjust Thresholds** - Fine-tune based on your environment
3. **Review Insights** - Check `/config/openai-watchdog/insights/`
4. **Optimize Costs** - Monitor daily expenses and adjust as needed

---

For additional help, see the main [README.md](README.md) or [DOCS.md](DOCS.md) files.