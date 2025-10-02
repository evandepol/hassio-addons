# Copilot Instructions - Home Assistant Add-ons Repository

## Repository Architecture

This is a Home Assistant add-ons repository (`hassio-addons`) containing multiple containerized add-ons that extend Home Assistant functionality. Each add-on follows the [Home Assistant add-on specification](https://developers.home-assistant.io/docs/add-ons/).

**Core Add-ons:**
- `claude-home/` - AI-powered terminal with Claude Code CLI integration
- `apcupsd/` - APC UPS monitoring with native apcupsd integration
- `hassio-access-point/` - WiFi hotspot functionality
- `claude-watchdog/` - Continuous AI monitoring for Home Assistant using Claude AI
- `openai-watchdog/` - Fork of claude-watchdog using OpenAI GPT models instead of Claude

## Add-on Structure Pattern

Every add-on directory contains these required files:
```
addon-name/
├── config.yaml          # Add-on metadata, options schema, permissions
├── build.yaml           # Multi-arch container build configuration  
├── Dockerfile           # Container image definition
├── run.sh               # Main entry point (#!/usr/bin/with-contenv bashio)
├── README.md           # User documentation
└── DOCS.md             # Detailed configuration docs
```

## Development Workflow

**Use the dev scripts in `dev/scripts/`** - never manually build add-ons:

```bash
# Start file watching for auto-rebuild (primary workflow)
./dev/scripts/dev-watch.sh claude-home &

# Build and deploy to specific environments
./dev/scripts/dev-build.sh claude-home haos     # VirtualBox HAOS (primary)
./dev/scripts/dev-build.sh claude-home hassdeb  # Debian Supervised
./dev/scripts/dev-build.sh claude-home hadocker # Standalone container

# Deploy all environments simultaneously  
./dev/scripts/dev-build-all.sh claude-home

# Clean development artifacts
./dev/scripts/dev-clean.sh
```

**Key Development Concepts:**
- Development versions use temporary timestamps (`dev-20250102-143022`) 
- Production versions stay in `config.yaml` - never commit dev versions
- `.dev-version` files are gitignored and track current dev builds
- Development environments: `haos` (primary), `hassdeb` (validation), `hadocker` (experimental)

## Home Assistant Integration Patterns

### Bashio Library Usage
All add-on entry scripts use `#!/usr/bin/with-contenv bashio` and the bashio library:

```bash
# Configuration access
local claude_model=$(bashio::config 'claude_model' 'claude-3-5-haiku-20241022')
local theme=$(bashio::config 'theme' 'dark')

# Logging with consistent format
bashio::log.info "Configuration: Model=$claude_model, Theme=$theme"
bashio::log.error "✗ Service failed to start"

# API calls to Home Assistant
bashio::api.supervisor GET /core/api/states false
bashio::api.supervisor POST /core/api/services/notify/persistent_notification \
  '{"message": "Hello from add-on"}'
```

### Home Assistant API Access
Add-ons use `hassio_api: true` permission to access HA via Supervisor proxy:

```bash
# Standard environment variables available in all add-ons
HA_URL="http://supervisor/core"
TOKEN="${SUPERVISOR_TOKEN:-$HASSIO_TOKEN}"

# Direct HTTP calls when bashio is not available
curl -X GET \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "${HA_URL}/api/states"
```

### Supervisor Integration
Add-ons can control the host system through Supervisor APIs:

```bash
# Host shutdown/reboot (see apcupsd/hassio_poweroff, hassio_reboot)
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "http://supervisor/host/shutdown"

# Auto-discovery for integrations (see apcupsd/scripts/auto-discovery.sh)
bashio::api.supervisor GET /addons false | jq '.addons[] | select(.slug == "apcupsd")'
```

## Configuration Schema Patterns

**Standard config.yaml structure:**
```yaml
name: "Add-on Name"
version: "1.0.0"  
slug: "addon_name"
arch: [aarch64, amd64]

# UI Integration
ingress: true                    # For web interfaces
ingress_port: 7681
panel_icon: mdi:icon-name
panel_admin: true               # Admin-only access

# Permissions (be minimal)
homeassistant_api: true         # Core HA API access
hassio_api: true               # Supervisor API access
host_network: true             # Only if network control needed
full_access: true              # Show protection mode toggle

# Volume mapping
map:
  - config:rw                  # Standard persistent storage
```

## Security and Resource Management

**File Permissions Pattern (see claude-home/run.sh):**
```bash
# Create config directories with restricted permissions
mkdir -p /config/addon-name
chmod 700 /config/addon-name

# Separate concerns with subdirectories
mkdir -p /config/addon-name/{data,cache,logs}
```

**AI Add-on Security Patterns:**
```bash
# API credential storage with secure permissions
mkdir -p /config/addon-name
chmod 700 /config/addon-name
# Credential file should be created by user, validated by add-on

# Cost tracking data structure
mkdir -p /config/addon-name/{insights,patterns,costs,logs}

# Environment variable handling
export OPENAI_API_KEY="$(cat /config/addon-name/credentials.json | jq -r '.api_key')"
```

**Environment Detection (standalone vs supervised):**
```bash
if [ -n "$SUPERVISOR_TOKEN" ]; then
    # Supervised add-on mode
    HA_URL="http://supervisor/core"
    HA_TOKEN="$SUPERVISOR_TOKEN"
else
    # Standalone container mode
    HA_URL="${HA_URL:-http://homeassistant.local:8123}"
    HA_TOKEN="${HA_TOKEN}"
fi
```

## Testing and Validation

**Local testing commands:**
```bash
# Build validation
docker run --rm -v $(pwd)/addon-name:/data homeassistant/amd64-builder --validate

# Dockerfile linting  
hadolint ./addon-name/Dockerfile

# Service testing
curl -X GET http://localhost:PORT/
```

**AI Add-on Testing Patterns:**
```bash
# Test with mock analysis (no API costs)
# Set environment to disable real API calls during development
export OPENAI_API_KEY=""  # Empty key triggers mock mode

# Cost tracking testing
# Monitor cost files during development
tail -f /config/addon-name/costs/daily_costs.json

# Integration testing with Home Assistant
# Use bashio::api.supervisor for HA state access in development
```

**CI/CD via GitHub Actions:**
- Multi-architecture builds (amd64, arm64) using Docker Buildx
- Container registry: `ghcr.io/cabinlab/addon-name`
- Automated builds on file changes in add-on directories
- See `.github/workflows/build-*.yml` for patterns

## Critical Integration Points

**Claude Home specific patterns:**
- MCP (Model Context Protocol) server integration in `hass-mcp-lite/`
- Natural language automation builder (`scripts/claude-automate.sh`)
- Home Assistant context integration (`scripts/ha-context.sh`)

**OpenAI Watchdog (fork development):**
- Based on `claude-watchdog/` but uses OpenAI GPT models instead of Claude
- **API Integration**: Uses `AsyncOpenAI` client with proper async/await patterns
- **Model Support**: `gpt-4o-mini` (default), `gpt-4o`, `gpt-3.5-turbo`
- **Configuration**: Uses `openai_model` instead of `claude_model`
- **Environment Variables**: `OPENAI_MODEL`, `OPENAI_WATCHDOG_DATA`
- **Dependencies**: `openai` Python package instead of `anthropic`
- **Directory Structure**: `/config/openai-watchdog/` with subdirs for insights, costs, logs
- **Cost Tracking**: Real-time token usage and cost calculation with OpenAI pricing
- **API Key Management**: Supports environment variables or `/config/openai-watchdog/credentials.json`
- **Structured Analysis**: JSON-formatted prompts and responses for consistent parsing
- **Error Handling**: Automatic fallback to mock analysis on API failures

**APC UPS specific patterns:**
- Native host control through Supervisor APIs (`hassio_poweroff`, `hassio_reboot`)  
- Event-driven scripts with UPS state monitoring
- Auto-discovery integration with Home Assistant's native apcupsd platform

**AI Add-on Patterns (claude-home, claude-watchdog, openai-watchdog):**
- **Credential Management**: Store API keys in `/config/addon-name/credentials.json`
- **Cost Tracking**: Implement daily limits with `cost_tracker.py` pattern
- **Environment Detection**: Support both supervised and standalone modes
- **Async Architecture**: Use asyncio for non-blocking API calls
- **Structured Prompts**: JSON-formatted requests for consistent AI responses
- **Mock Fallbacks**: Development/testing modes without API costs
- **Configuration Schema**: Model selection, thresholds, monitoring scope options

**Cross-add-on Communication:**
- Shared `/config` directory for inter-add-on data exchange
- Standard logging patterns for centralized monitoring
- Common credential storage patterns in `/config/addon-name`

## Repository Conventions

- **Branch strategy:** All development on `main` branch
- **Versioning:** Semantic versioning in `config.yaml`
- **Documentation:** Each add-on has README.md (user) and DOCS.md (technical)
- **Licensing:** MIT License for add-on code, respect third-party licenses
- **Issue templates:** Use repository discussions for support

---

*Consult `CLAUDE.md` for additional Claude-specific development guidance and `dev/DEVELOPMENT.md` for detailed development workflows.*