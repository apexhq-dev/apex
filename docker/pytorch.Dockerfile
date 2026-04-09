# apex/code-server:pytorch — CUDA + PyTorch + torchvision + code-server.
# Same image is used both for dev sessions (default CMD launches code-server)
# and for training jobs (Apex's scheduler overrides the command).
FROM pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates git dumb-init \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://code-server.dev/install.sh | sh

# torchvision is already included in pytorch/pytorch, but pin it to make the
# image self-contained in case the base image changes in the future.
RUN pip install --no-cache-dir torchvision tqdm

WORKDIR /workspace

ENTRYPOINT ["dumb-init", "--"]
CMD ["code-server", "--auth", "none", "--bind-addr", "0.0.0.0:8080", "/workspace"]
