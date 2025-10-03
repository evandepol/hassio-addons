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
WORKDIR /config

# Copy application files
COPY run.sh /run.sh
COPY watchdog/ /app/
RUN chmod +x /run.sh
RUN chmod +x /app/*.py

# Use exec form for better signal handling
CMD ["/run.sh"]