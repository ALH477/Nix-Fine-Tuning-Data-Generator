# Multi-stage Dockerfile for Nix Fine-tuning Data Generator
# Supports both x86_64 and ARM64 architectures
#
# Copyright (c) 2024-2025 DeMoD LLC
# Licensed under the MIT License

# Build stage
FROM python:3.11-slim-bookworm AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Runtime stage
FROM python:3.11-slim-bookworm

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set up environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

# Create workspace directory
WORKDIR /workspace

# Copy application files
COPY generator.py /app/generator.py
COPY search_api_simple.py /app/search_api_simple.py

# Create a non-root user
RUN useradd -m -u 1000 -s /bin/bash nixgen && \
    chown -R nixgen:nixgen /workspace

# Switch to non-root user
USER nixgen

# Set entrypoint
ENTRYPOINT ["python", "/app/generator.py"]

# Default command
CMD ["--help"]

# Metadata
LABEL org.opencontainers.image.title="Nix Fine-tuning Data Generator"
LABEL org.opencontainers.image.description="Generate training data for Nix-oriented LLMs"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="DeMoD LLC"
LABEL org.opencontainers.image.source="https://github.com/yourusername/nix-finetune-generator"
LABEL org.opencontainers.image.documentation="https://github.com/yourusername/nix-finetune-generator/blob/main/README.md"
