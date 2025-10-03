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
    local local_model=$(bashio::config 'local_model' 'llama-3.2-3b')
    # Deprecated: local_model_path now controlled by bundled model
    local local_server_port=$(bashio::config 'local_server_port' '8088')
    local local_n_threads=$(bashio::config 'local_n_threads' '0')
    local local_max_cpu_load=$(bashio::config 'local_max_cpu_load' '1.5')
    local local_max_runtime_ms=$(bashio::config 'local_max_runtime_ms' '3000')
    local accept_model_license=$(bashio::config 'accept_model_license' 'false')
    local local_model_url=$(bashio::config 'local_model_url' '')
    local local_model_sha256=$(bashio::config 'local_model_sha256' '')
    local huggingface_token=$(bashio::config 'huggingface_token' '')
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
        export WATCHDOG_LOCAL_MODEL="$local_model"
        # Deterministic bundled path for supported model(s)
        case "$local_model" in
            "llama-3.2-3b")
                export WATCHDOG_LOCAL_MODEL_PATH="${WATCHDOG_BUNDLED_MODEL:-/opt/models/llama-3.2-3b-instruct-q4_k_m.gguf}"
                ;;
            *)
                bashio::log.error "Unsupported local_model: $local_model"
                export WATCHDOG_LOCAL_MODEL_PATH=""
                ;;
        esac
    export WATCHDOG_LOCAL_SERVER_PORT="$local_server_port"
    export WATCHDOG_LOCAL_N_THREADS="$local_n_threads"
    export WATCHDOG_LOCAL_MAX_CPU_LOAD="$local_max_cpu_load"
    export WATCHDOG_LOCAL_MAX_RUNTIME_MS="$local_max_runtime_ms"
    export WATCHDOG_ACCEPT_MODEL_LICENSE="$accept_model_license"
    export WATCHDOG_LOCAL_MODEL_URL="$local_model_url"
    export WATCHDOG_LOCAL_MODEL_SHA256="$local_model_sha256"
    export HUGGINGFACE_TOKEN="$huggingface_token"
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

    # If local model file is missing but a URL is provided and user accepted license, download now
    if [ "$local_enabled" = "true" ] && [ -z "$local_base_url" ]; then
        # Provide a default URL for supported models when user hasn't set one
        if [ -z "$local_model_url" ]; then
            case "$local_model" in
                "llama-3.2-3b")
                    # Default GGUF URL for Llama 3.2 3B Instruct Q4_K_M (community GGUF conversion)
                    # Note: Download may require accepting the model license on the hosting site.
                    local_model_url="${WATCHDOG_DEFAULT_MODEL_URL:-https://huggingface.co/TheBloke/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct.Q4_K_M.gguf}"
                    # Optional: provide default checksum via env WATCHDOG_DEFAULT_MODEL_SHA256 if desired
                    if [ -z "$local_model_sha256" ] && [ -n "${WATCHDOG_DEFAULT_MODEL_SHA256:-}" ]; then
                        local_model_sha256="$WATCHDOG_DEFAULT_MODEL_SHA256"
                    fi
                    ;;
            esac
        fi

        if [ ! -f "$WATCHDOG_LOCAL_MODEL_PATH" ] && [ -n "$local_model_url" ]; then
            if [ "$accept_model_license" != "true" ]; then
                bashio::log.error "Model URL provided but 'accept_model_license' is false. Refusing to download."
            else
                bashio::log.info "Downloading local model to $WATCHDOG_LOCAL_MODEL_PATH from $local_model_url"
                mkdir -p "$(dirname "$WATCHDOG_LOCAL_MODEL_PATH")"
                export WATCHDOG_LOCAL_MODEL_URL_USED="$local_model_url"
                DOWNLOAD_OK=0
                HDR_AUTH=""
                if [ -n "$huggingface_token" ]; then
                    HDR_AUTH="Authorization: Bearer $huggingface_token"
                fi
                if command -v curl >/dev/null 2>&1; then
                    if [ -n "$HDR_AUTH" ]; then
                        if curl -fL --retry 3 --retry-delay 2 -H "$HDR_AUTH" -o "$WATCHDOG_LOCAL_MODEL_PATH" "$local_model_url"; then
                            DOWNLOAD_OK=1
                        fi
                    else
                        if curl -fL --retry 3 --retry-delay 2 -o "$WATCHDOG_LOCAL_MODEL_PATH" "$local_model_url"; then
                            DOWNLOAD_OK=1
                        fi
                    fi
                else
                    if [ -n "$HDR_AUTH" ]; then
                        if wget --header="$HDR_AUTH" -q --tries=3 -O "$WATCHDOG_LOCAL_MODEL_PATH" "$local_model_url"; then
                            DOWNLOAD_OK=1
                        fi
                    else
                        if wget -q --tries=3 -O "$WATCHDOG_LOCAL_MODEL_PATH" "$local_model_url"; then
                            DOWNLOAD_OK=1
                        fi
                    fi
                fi
                if [ "$DOWNLOAD_OK" -ne 1 ]; then
                    bashio::log.error "Model download failed (HTTP error)."
                    export WATCHDOG_LOCAL_MODEL_DOWNLOAD_ERROR="download_failed"
                    rm -f "$WATCHDOG_LOCAL_MODEL_PATH" 2>/dev/null || true
                else
                    # Basic sanity check: require at least ~1MB to avoid HTML error pages
                    sz=$(wc -c < "$WATCHDOG_LOCAL_MODEL_PATH" 2>/dev/null || echo 0)
                    if [ "$sz" -lt 1000000 ]; then
                        bashio::log.error "Downloaded file is too small ($sz bytes). Likely a gated URL or error page."
                        export WATCHDOG_LOCAL_MODEL_DOWNLOAD_ERROR="file_too_small"
                        rm -f "$WATCHDOG_LOCAL_MODEL_PATH" 2>/dev/null || true
                    else
                        if [ -n "$local_model_sha256" ]; then
                            if echo "$local_model_sha256  $WATCHDOG_LOCAL_MODEL_PATH" | sha256sum -c -; then
                                bashio::log.info "Model checksum verified"
                            else
                                bashio::log.error "Checksum verification failed for downloaded model"
                                export WATCHDOG_LOCAL_MODEL_DOWNLOAD_ERROR="checksum_failed"
                                rm -f "$WATCHDOG_LOCAL_MODEL_PATH"
                            fi
                        fi
                        chmod 0644 "$WATCHDOG_LOCAL_MODEL_PATH" || true
                    fi
                fi
            fi
        fi
    fi
}

# Setup Home Assistant API access
setup_ha_access() {
    bashio::log.info "Setting up Home Assistant API access..."
    
    # Detect environment: supervised vs standalone
    if [ -n "${SUPERVISOR_TOKEN:-}" ]; then
        # Supervised add-on mode
        export HASSIO_TOKEN="${SUPERVISOR_TOKEN}"
        export HA_URL="http://supervisor/core"
        # Test API connectivity
        if curl -s -H "Authorization: Bearer ${HASSIO_TOKEN}" "${HA_URL}/api/" > /dev/null; then
            bashio::log.info "Home Assistant API connection successful"
        else
            bashio::log.error "Failed to connect to Home Assistant API"
            exit 1
        fi
    else
        # Standalone/container mode for local testing
        export HA_URL="${HA_URL:-http://homeassistant.local:8123}"
        export HASSIO_TOKEN="${HASSIO_TOKEN:-}"
        bashio::log.info "Standalone mode detected: HA_URL=${HA_URL}"
        bashio::log.info "Skipping Supervisor API connectivity check"
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
            if [ -f "$WATCHDOG_LOCAL_MODEL_PATH" ]; then
                bashio::log.info "Launching embedded llama.cpp server on port ${WATCHDOG_LOCAL_SERVER_PORT} with model ${WATCHDOG_LOCAL_MODEL_PATH}"
                mkdir -p /config/openai-watchdog/models
                # Start server in background
                                GGML_QNT_K_S=1 python3 -m llama_cpp.server \
                  --model "$WATCHDOG_LOCAL_MODEL_PATH" \
                  --host 0.0.0.0 \
                  --port "$WATCHDOG_LOCAL_SERVER_PORT" \
                  --n_threads "$WATCHDOG_LOCAL_N_THREADS" \
                                    --chat_format openai &
                LOCAL_SRV_PID=$!
                echo $LOCAL_SRV_PID > /var/run/watchdog_local_llm.pid || true
                # Export discovered base URL for the analyzer
                export WATCHDOG_LOCAL_BASE_URL="http://127.0.0.1:${WATCHDOG_LOCAL_SERVER_PORT}"
                bashio::log.info "Embedded local LLM available at ${WATCHDOG_LOCAL_BASE_URL}"
                # Give the server a moment to start
                sleep 2
            else
                bashio::log.error "Local provider enabled but bundled model not present at $WATCHDOG_LOCAL_MODEL_PATH; running without local server"
            fi
        fi
    fi

    # Start the Python monitoring application (PID 1)
    cd /app
    # Ensure Python can find our package (deterministic, no fallback)
    export PYTHONPATH="/app"
    exec python3 -m watchdog.main
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