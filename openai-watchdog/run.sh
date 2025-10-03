#!/usr/bin/with-contenv bashio

# Initialize monitoring environment
init_environment() {
    # Ensure monitoring data directory exists with proper permissions
    mkdir -p /config/openai-watchdog
    chmod 700 /config/openai-watchdog
    
    # Create subdirectories for different data types
    mkdir -p /config/openai-watchdog/{insights,patterns,costs,logs}
    
    # Set environment variables
    export OPENAI_WATCHDOG_DATA="/config/openai-watchdog"
    export HOME="/root"
    
    # Read configuration from Home Assistant
    local openai_api_key=$(bashio::config 'openai_api_key' '')
    local openai_model=$(bashio::config 'openai_model' 'gpt-4o-mini')
    local check_interval=$(bashio::config 'check_interval' '30')
    local insight_threshold=$(bashio::config 'insight_threshold' '0.8')
    local max_daily_calls=$(bashio::config 'max_daily_api_calls' '1000')
    local cost_limit=$(bashio::config 'cost_limit_daily' '1.00')
    local enable_learning=$(bashio::config 'enable_learning' 'true')
    
    # Export configuration as environment variables
    export OPENAI_API_KEY="$openai_api_key"
    export OPENAI_MODEL="$openai_model"
    export WATCHDOG_CHECK_INTERVAL="$check_interval"
    export WATCHDOG_INSIGHT_THRESHOLD="$insight_threshold"
    export WATCHDOG_MAX_DAILY_CALLS="$max_daily_calls"
    export WATCHDOG_COST_LIMIT="$cost_limit"
    export WATCHDOG_ENABLE_LEARNING="$enable_learning"
    
    # Get monitoring scope from config: could be YAML list or string
    local scope_json
    if bashio::config.has_value 'monitoring_scope'; then
        scope_json=$(bashio::config 'monitoring_scope')
    else
        scope_json='all'
    fi
    # Normalize to lowercase
    scope_json=$(echo "$scope_json" | tr '[:upper:]' '[:lower:]')
    export WATCHDOG_MONITORING_SCOPE="$scope_json"
    
    # Notification service
    local notification_service=$(bashio::config 'notification_service' 'persistent_notification')
    export WATCHDOG_NOTIFICATION_SERVICE="$notification_service"
    
    # Validate API key configuration
    if [ -z "$openai_api_key" ]; then
        bashio::log.error "❌ No OpenAI API key configured"
        bashio::log.error "Please set 'openai_api_key' in the add-on configuration UI"
        bashio::log.error "Add-on will run in mock analysis mode"
    else
        bashio::log.info "✅ OpenAI API key configured"
    fi
    
    bashio::log.info "OpenAI Watchdog configured with model: $openai_model"
    bashio::log.info "Check interval: ${check_interval}s, Cost limit: \$${cost_limit}/day"
}

# Setup Home Assistant API access
setup_ha_access() {
    bashio::log.info "Setting up Home Assistant API access..."
    
    # Get Home Assistant details
    # Supervisor injects SUPERVISOR_TOKEN; keep HASSIO_TOKEN for backward compat
    export HASSIO_TOKEN="${SUPERVISOR_TOKEN:-$HASSIO_TOKEN}"
    export HA_URL="http://supervisor/core"
    
    # Test API connectivity
    if curl -s -H "Authorization: Bearer ${HASSIO_TOKEN}" "${HA_URL}/api/" > /dev/null; then
        bashio::log.info "Home Assistant API connection successful"
    else
        bashio::log.error "Failed to connect to Home Assistant API"
        exit 1
    fi
}

# Start the monitoring service
start_monitoring_service() {
    bashio::log.info "Starting OpenAI Watchdog monitoring service..."
    
    # Log environment information for debugging
    bashio::log.info "Environment variables:"
    bashio::log.info "OPENAI_MODEL=${OPENAI_MODEL}"
    bashio::log.info "WATCHDOG_CHECK_INTERVAL=${WATCHDOG_CHECK_INTERVAL}"
    bashio::log.info "WATCHDOG_COST_LIMIT=${WATCHDOG_COST_LIMIT}"
    
    # Start the Python monitoring application
    cd /app
    exec python3 main.py
}

# Main execution
main() {
    bashio::log.info "Initializing OpenAI Watchdog add-on..."
    
    init_environment
    setup_ha_access
    start_monitoring_service
}

# Execute main function
main "$@"