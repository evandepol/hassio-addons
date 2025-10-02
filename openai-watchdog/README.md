# OpenAI Watchdog for Home Assistant

[![Open your Home Assistant instance and show the dashboard of a Supervisor add-on.](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=openai_watchdog&repository_url=https%3A%2F%2Fgithub.com%2Fcabinlab%2Fhassio-addons)

Intelligent continuous monitoring for Home Assistant using OpenAI. OpenAI Watchdog runs in the background, analyzing your system state changes and providing proactive insights, security monitoring, and optimization recommendations.

## What is OpenAI Watchdog?

OpenAI Watchdog is a revolutionary Home Assistant add-on that provides:

- **Continuous AI Monitoring**: Uses OpenAI GPT models for intelligent, cost-effective analysis
- **Proactive Insights**: Identifies patterns and anomalies before they become problems
- **Intelligent Alerts**: Smart notifications based on confidence levels and context
- **Energy Optimization**: Detects efficiency opportunities and wasteful patterns
- **Security Intelligence**: Advanced anomaly detection for security events
- **Automation Health**: Monitors automation performance and suggests improvements

## Features

- **Real-time State Analysis**: Monitors entity state changes across your Home Assistant system
- **Multi-Domain Monitoring**: Climate, security, energy, automation performance, and device health
- **Cost-Controlled**: Built-in cost tracking with daily limits to prevent unexpected charges
- **Smart Analysis**: Uses OpenAI GPT models for intelligent pattern recognition
- **Structured Insights**: JSON-formatted analysis with confidence levels and recommended actions
- **Smart Notifications**: Configurable alerts via Home Assistant notification services
- **Comprehensive Logging**: Detailed insights and analysis history
- **Development Mode**: Mock analysis for testing without API costs

## Installation

### Quick Install
[![Open your Home Assistant instance and show the dashboard of a Supervisor add-on.](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=openai_watchdog&repository_url=https%3A%2F%2Fgithub.com%2Fcabinlab%2Fhassio-addons)

### Manual Installation
1. Add this repository to your Home Assistant add-on store:

   [![Open your Home Assistant instance and show the add add-on repository dialog with this repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fcabinlab%2Fhassio-addons)

2. Install the "OpenAI Watchdog" add-on
3. Configure your monitoring preferences (see configuration section below)
4. Start the add-on
5. Configure your OpenAI API credentials (see credentials section)

## Configuration

### Basic Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `openai_api_key` | Your OpenAI API key | `""` (required) |
| `openai_model` | OpenAI model to use for analysis | `gpt-4o-mini` |
| `check_interval` | Seconds between monitoring checks | `30` |
| `insight_threshold` | Confidence threshold for alerts (0.0-1.0) | `0.8` |
| `max_daily_api_calls` | Maximum API calls per day | `1000` |
| `cost_limit_daily` | Maximum daily cost in USD | `1.00` |
| `notification_service` | HA notification service to use | `persistent_notification` |
| `enable_learning` | Enable pattern learning | `true` |

### Monitoring Scope

Select which areas to monitor:

- **climate**: Temperature, humidity, HVAC systems
- **security**: Doors, locks, motion sensors, alarms
- **energy**: Power consumption, efficiency monitoring
- **automation_performance**: Automation execution and health
- **device_health**: Device connectivity and battery status
- **patterns**: General behavior pattern analysis

### Example Configuration

```yaml
openai_api_key: "sk-your-openai-api-key-here"
openai_model: "gpt-4o-mini"
check_interval: 30
insight_threshold: 0.8
max_daily_api_calls: 1000
monitoring_scope:
  - "climate"
  - "security"
  - "energy"
cost_limit_daily: 1.00
notification_service: "notify"
enable_learning: true
```

## Setting Up OpenAI API Credentials

OpenAI Watchdog requires an OpenAI API key to function:

1. **Get an OpenAI API Key**: Visit [platform.openai.com](https://platform.openai.com/) to create an account and generate an API key

2. **Configure in Home Assistant**: 
   - Go to **Settings** → **Add-ons** → **OpenAI Watchdog**
   - Click the **Configuration** tab
   - Enter your OpenAI API key in the `openai_api_key` field
   - Configure other settings as needed
   - Click **Save** and restart the add-on

## Cost Management

OpenAI Watchdog is designed to be cost-effective:

### Default Limits
- **Daily Cost Limit**: $1.00 USD per day
- **Daily API Calls**: 1,000 requests maximum
- **Model**: GPT-4o-mini (fastest, most cost-effective)

### OpenAI Model Pricing (per 1K tokens)
- **GPT-4o-mini**: $0.15 input / $0.60 output (recommended)
- **GPT-4o**: $2.50 input / $10.00 output (most capable)
- **GPT-3.5-turbo**: $0.50 input / $1.50 output (balanced)

### Estimated Costs
- **Check Interval**: 30 seconds = 2,880 potential checks/day
- **Actual Usage**: Smart filtering reduces to ~200-500 API calls/day
- **Average Cost**: ~$0.20-0.50/day with GPT-4o-mini
- **Monthly Cost**: ~$6-15/month for intelligent monitoring

### Cost Tracking
- Real-time cost tracking with automatic limits
- Detailed usage statistics and history
- Automatic daily reset of usage counters

## Use Cases

### Predictive Maintenance
```
"Water heater temperature gradually increasing over 3 weeks. 
Recommend scheduling maintenance before potential failure."
```

### Energy Optimization  
```
"HVAC runtime increased 23% this week despite similar weather.
Possible causes: dirty filter, leaky ducts, or schedule inefficiency."
```

### Security Intelligence
```
"Motion patterns suggest unusual activity. 
Recommend reviewing exterior camera footage from 2-4pm daily."
```

### Automation Health
```
"Kitchen lights automation failed 3x this week.
Motion sensor may need recalibration or battery replacement."
```

## Understanding Insights

OpenAI Watchdog provides different types of insights:

### Insight Types
- **Security**: Unusual access patterns, motion anomalies
- **Energy**: Consumption spikes, efficiency opportunities  
- **Climate**: Temperature control optimization, HVAC patterns
- **Automation**: Performance issues, failed executions
- **Device Health**: Connectivity problems, maintenance needs
- **General**: Pattern recognition, behavioral insights

### Confidence Levels
- **High (0.8-1.0)**: Immediate attention recommended
- **Medium (0.6-0.8)**: Worth investigating
- **Low (0.4-0.6)**: Informational observation

## Notifications

Configure how you receive insights:

### Persistent Notifications (Default)
- Appear in Home Assistant frontend
- Persistent until dismissed
- Include full insight details

### Mobile/Email Notifications
- Configure any Home Assistant notification service
- Set `notification_service` to your preferred service
- Examples: `mobile_app_phone`, `smtp`, `telegram_bot`

## Data Storage

OpenAI Watchdog stores data in `/config/openai-watchdog/`:

- `insights/`: Analysis results and recommendations
- `patterns/`: Learned behavior patterns (future feature)
- `costs/`: API usage and cost tracking
- `logs/`: Service logs and debug information

## Troubleshooting

### Common Issues

1. **High API Costs**: Adjust `check_interval` or `cost_limit_daily` in add-on configuration
2. **Too Many Alerts**: Increase `insight_threshold` value in add-on configuration
3. **Missing Insights**: Lower `insight_threshold` or check monitoring scope in configuration
4. **API Errors**: Verify OpenAI API key is correctly entered in add-on configuration
5. **No Analysis**: Ensure `openai_api_key` is set in the add-on configuration UI
6. **Configuration Issues**: Check add-on logs for configuration validation errors

### Logs

View add-on logs for detailed information:
- Service startup and configuration
- API usage and costs
- Analysis results and insights
- Error messages and debugging info

## Technical Implementation

### API Integration
- **AsyncOpenAI Client**: Full async/await support for non-blocking operations
- **Structured Prompts**: JSON-formatted responses for consistent parsing
- **Cost Tracking**: Real-time token usage and cost calculation
- **Error Handling**: Automatic fallback to mock analysis on API failures
- **Rate Limiting**: Built-in daily cost and request limits

### Smart Analysis
- **Context Awareness**: Analyzes patterns across multiple state changes
- **Confidence Scoring**: Only alerts on high-confidence insights (>0.8)
- **Domain-Specific**: Tailored analysis for climate, security, energy, etc.
- **Learning Ready**: Architecture supports future pattern learning features

## Privacy and Security

- **Local Processing**: Only state changes are sent to OpenAI API
- **No Personal Data**: Entity IDs and states only, no personal information
- **Secure Configuration**: API keys handled securely through Home Assistant configuration UI
- **Configurable Scope**: Monitor only the domains you choose
- **Data Isolation**: Monitoring data stored in dedicated add-on directory

## Support

- [Documentation](https://github.com/cabinlab/hassio-addons)
- [Issue Tracker](https://github.com/cabinlab/hassio-addons/issues)  
- [OpenAI API Documentation](https://platform.openai.com/docs/)

## Credits

Built by Cabin Assistant for intelligent home automation monitoring.