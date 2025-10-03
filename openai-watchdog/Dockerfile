ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install packages for monitoring service (Debian-based HA base)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-aiohttp \
        python3-venv \
        bash \
        curl \
        jq \
    && pip3 install --no-cache-dir \
        openai \
        pyyaml \
        schedule \
        python-dateutil \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create directory for monitoring data
RUN mkdir -p /config/openai-watchdog
WORKDIR /config

# Copy application files
COPY run.sh /run.sh
COPY watchdog/ /app/
RUN chmod +x /run.sh \
    && chmod +x /app/*.py

# Use exec form for better signal handling
CMD ["/run.sh"]