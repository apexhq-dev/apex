# apex/code-server:python — slim Python dev image with code-server pre-installed.
# Use for lightweight dev sessions and CPU-only jobs.
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates git dumb-init \
    && rm -rf /var/lib/apt/lists/*

# code-server — the standalone install script works on glibc Linux.
RUN curl -fsSL https://code-server.dev/install.sh | sh

# A handful of sane Python defaults for quick scripting.
RUN pip install --no-cache-dir numpy pandas requests

WORKDIR /workspace

# Default command runs code-server for dev sessions. Apex's scheduler
# overrides this with the training script when a job is submitted.
ENTRYPOINT ["dumb-init", "--"]
CMD ["code-server", "--auth", "none", "--bind-addr", "0.0.0.0:8080", "/workspace"]
