ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install packages for monitoring service (Alpine-based HA base)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-aiohttp \
    bash \
    curl \
    jq

# Resolve musl/musl-dev mismatch and add build toolchain
RUN apk update
RUN apk upgrade --no-cache --available musl musl-utils
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    cmake \
    ninja \
    pkgconf

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
RUN apk del .build-deps

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