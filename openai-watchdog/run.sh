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
    local openai_base_url=$(bashio::config 'openai_base_url' '')
    local openai_model=$(bashio::config 'openai_model' 'gpt-4o-mini')
    local mode=$(bashio::config 'mode' 'auto')
    local local_enabled=$(bashio::config 'local_enabled' 'false')
    local local_base_url=$(bashio::config 'local_base_url' '')
    local local_provider=$(bashio::config 'local_provider' 'llama_cpp')
    local local_model_path=$(bashio::config 'local_model_path' '')
    local local_server_port=$(bashio::config 'local_server_port' '8088')
    local local_n_threads=$(bashio::config 'local_n_threads' '0')
    local local_max_cpu_load=$(bashio::config 'local_max_cpu_load' '1.5')
    local local_max_runtime_ms=$(bashio::config 'local_max_runtime_ms' '3000')
    local check_interval=$(bashio::config 'check_interval' '30')
    local insight_threshold=$(bashio::config 'insight_threshold' '0.8')
    local max_daily_calls=$(bashio::config 'max_daily_api_calls' '1000')
    local cost_limit=$(bashio::config 'cost_limit_daily' '1.00')
    local enable_learning=$(bashio::config 'enable_learning' 'true')
    local log_api_payloads_to_stdout=$(bashio::config 'log_api_payloads_to_stdout' 'false')
    local notify_on_any_insight=$(bashio::config 'notify_on_any_insight' 'false')
    local send_test_notification_on_start=$(bashio::config 'send_test_notification_on_start' 'true')
    
    # Export configuration as environment variables
    export OPENAI_API_KEY="$openai_api_key"
    export OPENAI_BASE_URL="$openai_base_url"
    export OPENAI_MODEL="$openai_model"
    export WATCHDOG_MODE="$mode"
    export WATCHDOG_LOCAL_ENABLED="$local_enabled"
    export WATCHDOG_LOCAL_BASE_URL="$local_base_url"
    export WATCHDOG_LOCAL_PROVIDER="$local_provider"
    export WATCHDOG_LOCAL_MODEL_PATH="$local_model_path"
    export WATCHDOG_LOCAL_SERVER_PORT="$local_server_port"
    export WATCHDOG_LOCAL_N_THREADS="$local_n_threads"
    export WATCHDOG_LOCAL_MAX_CPU_LOAD="$local_max_cpu_load"
    export WATCHDOG_LOCAL_MAX_RUNTIME_MS="$local_max_runtime_ms"
    export WATCHDOG_CHECK_INTERVAL="$check_interval"
    export WATCHDOG_INSIGHT_THRESHOLD="$insight_threshold"
    export WATCHDOG_MAX_DAILY_CALLS="$max_daily_calls"
    export WATCHDOG_COST_LIMIT="$cost_limit"
    export WATCHDOG_ENABLE_LEARNING="$enable_learning"
    export WATCHDOG_LOG_API_STDOUT="$log_api_payloads_to_stdout"
    export WATCHDOG_NOTIFY_ON_ANY_INSIGHT="$notify_on_any_insight"
    export WATCHDOG_SEND_TEST_NOTIFICATION="$send_test_notification_on_start"
    export WATCHDOG_HTTP_PORT="8099"
    
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
    if [ -n "$openai_base_url" ]; then
        bashio::log.info "Using custom OpenAI base URL: $openai_base_url"
    fi
    if [ "$local_enabled" = "true" ]; then
        bashio::log.info "Local provider enabled (base URL: ${local_base_url:-not set}, provider: ${local_provider})"
    fi
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
    
    # Optionally start embedded local LLM server if enabled and no explicit base URL is set
    if [ "$WATCHDOG_LOCAL_ENABLED" = "true" ] && [ -z "$WATCHDOG_LOCAL_BASE_URL" ]; then
        if [ "$WATCHDOG_LOCAL_PROVIDER" = "llama_cpp" ]; then
            if [ -z "$WATCHDOG_LOCAL_MODEL_PATH" ]; then
                bashio::log.error "Local provider enabled but no local_model_path set; running without local server"
            else
                bashio::log.info "Launching embedded llama.cpp server on port ${WATCHDOG_LOCAL_SERVER_PORT} with model ${WATCHDOG_LOCAL_MODEL_PATH}"
                mkdir -p /config/openai-watchdog/models
                # Start server in background
                GGML_QNT_K_S=1 python3 -m llama_cpp.server \
                  --model "$WATCHDOG_LOCAL_MODEL_PATH" \
                  --host 0.0.0.0 \
                  --port "$WATCHDOG_LOCAL_SERVER_PORT" \
                  --n_threads "$WATCHDOG_LOCAL_N_THREADS" \
                  --chat-format openai &
                LOCAL_SRV_PID=$!
                echo $LOCAL_SRV_PID > /var/run/watchdog_local_llm.pid || true
                # Export discovered base URL for the analyzer
                export WATCHDOG_LOCAL_BASE_URL="http://127.0.0.1:${WATCHDOG_LOCAL_SERVER_PORT}"
                bashio::log.info "Embedded local LLM available at ${WATCHDOG_LOCAL_BASE_URL}"
                # Give the server a moment to start
                sleep 2
            fi
        fi
    fi

    # Start the Python monitoring application (PID 1)
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