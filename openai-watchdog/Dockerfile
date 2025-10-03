ARG BUILD_FROM=ghcr.io/hassio-addons/base:16.0.1
FROM ${BUILD_FROM}

# Install packages for monitoring service (Alpine-based HA base)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-aiohttp \
    bash \
    curl \
    jq

# Resolve musl/musl-dev mismatch and add build toolchain (single layer to avoid stale cache)
RUN set -eux; \
    # Unpin musl packages from world to allow upgrade if the base image pinned exact versions
    sed -i -E 's/^musl=[^[:space:]]+$/musl/' /etc/apk/world || true; \
    sed -i -E 's/^musl-utils=[^[:space:]]+$/musl-utils/' /etc/apk/world || true; \
    apk update; \
    apk upgrade --no-cache --available; \
    apk add --no-cache \
            build-base \
            cmake \
            ninja \
            pkgconf \
            musl-dev \
            linux-headers

# Configure llama.cpp build (CPU-only) and prefer prebuilt wheels when available
ENV CMAKE_ARGS="-DLLAMA_CUBLAS=OFF -DLLAMA_METAL=OFF -DLLAMA_OPENBLAS=OFF -DLLAMA_BLAS=OFF"
ENV LLAMA_CPP_PYTHON_PREBUILT=TRUE

# Python dependencies (including embedded llama.cpp server)
RUN pip3 install --no-cache-dir \
    openai \
    pyyaml \
    schedule \
    python-dateutil \
    llama-cpp-python[server]==0.2.90

# Remove build dependencies to keep image small
RUN apk del build-base cmake ninja pkgconf musl-dev linux-headers || true

# Create directory for monitoring data
RUN mkdir -p /config/openai-watchdog
RUN mkdir -p /opt/models
ENV WATCHDOG_BUNDLED_MODEL="/opt/models/llama-3.2-3b-instruct-q4_k_m.gguf"
WORKDIR /config

# Copy application files
COPY run.sh /run.sh
COPY watchdog/ /app/watchdog/

# Optionally bundle a model at build time (provide BUNDLE_MODEL_URL and optional BUNDLE_MODEL_SHA256)
ARG BUNDLE_MODEL_URL=""
ARG BUNDLE_MODEL_SHA256=""
ENV WATCHDOG_BUNDLED_MODEL_SHA256="$BUNDLE_MODEL_SHA256"
RUN set -eux; \
        if [ -n "$BUNDLE_MODEL_URL" ]; then \
            echo "Downloading bundled model from $BUNDLE_MODEL_URL"; \
            apk add --no-cache curl ca-certificates; \
            curl -L "$BUNDLE_MODEL_URL" -o "$WATCHDOG_BUNDLED_MODEL"; \
            if [ -n "$BUNDLE_MODEL_SHA256" ]; then \
                echo "$BUNDLE_MODEL_SHA256  $WATCHDOG_BUNDLED_MODEL" | sha256sum -c -; \
                echo "Model checksum verified"; \
            else \
                echo "No BUNDLE_MODEL_SHA256 provided; skipping checksum validation"; \
            fi; \
            chmod 0644 "$WATCHDOG_BUNDLED_MODEL"; \
        else \
            echo "No BUNDLE_MODEL_URL provided; building without embedded model"; \
        fi
RUN chmod +x /run.sh
RUN chmod +x /app/watchdog/*.py

# Use exec form for better signal handling
CMD ["/run.sh"]