# ===== Dockerfile =====
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# --- System deps for Meshroom/AliceVision CLIs + Python API + GLB conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates curl zip \
    libgl1-mesa-glx libglu1-mesa libxrandr2 libxinerama1 libxi6 libxrender1 \
    libxxf86vm1 libxkbcommon0 libjpeg-turbo8 libpng16-16 libtiff5 ffmpeg \
    python3 python3-pip python3-venv \
    assimp-utils \
 && rm -rf /var/lib/apt/lists/*

# --- Meshroom bundle from HF (public or private)
ARG HF_FILE_URL="https://huggingface.co/datasets/ericos1234/alice_data/resolve/main/Meshroom-2023.3.0-linux.tar.gz"

RUN set -eux; \
    if [ -z "${HF_TOKEN:-}" ]; then \
      echo "Downloading (public) $HF_FILE_URL"; \
      curl -fL --retry 5 --retry-delay 2 -o /tmp/meshroom.tar.gz "$HF_FILE_URL"; \
    else \
      echo "Downloading (private) $HF_FILE_URL with token"; \
      curl -fL --retry 5 --retry-delay 2 -H "Authorization: Bearer $HF_TOKEN" \
        -o /tmp/meshroom.tar.gz "$HF_FILE_URL"; \
    fi; \
    mkdir -p /opt/meshroom; \
    tar -xzf /tmp/meshroom.tar.gz -C /opt/meshroom --strip-components=1; \
    rm /tmp/meshroom.tar.gz

# Make Meshroom CLIs available (meshroom_photogrammetry, etc.)
ENV PATH="/opt/meshroom:${PATH}"

# --- Python deps
RUN python3 -m pip install --no-cache-dir fastapi uvicorn[standard] pillow

# --- App code
WORKDIR /app
COPY server.py /app/server.py
COPY utils.py  /app/utils.py

# --- Work dirs
RUN mkdir -p /data/work /data/out

# --- Expose API port
EXPOSE 7860

# --- Start FastAPI app
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
