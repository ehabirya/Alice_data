# ===== Meshroom Headless API Dockerfile =====
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# --- System deps for Meshroom + GLB conversion ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates curl zip \
    libgl1-mesa-glx libglu1-mesa libxrandr2 libxinerama1 libxi6 libxrender1 \
    libxxf86vm1 libxkbcommon0 libjpeg-turbo8 libpng16-16 libtiff5 ffmpeg \
    python3 python3-pip python3-venv \
    assimp-utils \
 && rm -rf /var/lib/apt/lists/*

# --- Download Meshroom from Hugging Face (with GitHub fallback) ---
ARG HF_FILE_URL="https://huggingface.co/datasets/ericos1234/alice_data/resolve/main/Meshroom-2023.3.0-linux.tar.gz"
ARG HF_TOKEN
ENV FALLBACK_URL="https://github.com/alicevision/meshroom/releases/download/v2023.3.0/Meshroom-2023.3.0-linux.tar.gz"

RUN set -eux; \
  echo "➡️  Checking Hugging Face URL: ${HF_FILE_URL}"; \
  if [ -n "${HF_TOKEN:-}" ]; then \
    echo "🔐 Private download with token..."; \
    curl -I -H "Authorization: Bearer ${HF_TOKEN}" -L "${HF_FILE_URL}" || true; \
    curl -fL --retry 5 --retry-delay 2 -H "Authorization: Bearer ${HF_TOKEN}" \
      -o /tmp/meshroom.tar.gz "${HF_FILE_URL}" \
      || (echo "⚠️  HF download failed, using fallback"; curl -fL -o /tmp/meshroom.tar.gz "${FALLBACK_URL}"); \
  else \
    echo "🌍 Public download..."; \
    curl -I -L "${HF_FILE_URL}" || true; \
    curl -fL --retry 5 --retry-delay 2 -o /tmp/meshroom.tar.gz "${HF_FILE_URL}" \
      || (echo "⚠️  HF download failed, using fallback"; curl -fL -o /tmp/meshroom.tar.gz "${FALLBACK_URL}"); \
  fi; \
  mkdir -p /opt/meshroom; \
  tar -xzf /tmp/meshroom.tar.gz -C /opt/meshroom --strip-components=1; \
  rm /tmp/meshroom.tar.gz

# --- Make Meshroom binaries available globally ---
ENV PATH="/opt/meshroom:${PATH}"

# --- Python deps for FastAPI server ---
RUN python3 -m pip install --no-cache-dir fastapi uvicorn[standard] pillow

# --- Copy app code ---
WORKDIR /app
COPY server.py /app/server.py
COPY utils.py  /app/utils.py

# --- Work dirs for temp & output ---
RUN mkdir -p /data/work /data/out

# --- Expose port (Runpod/HF default) ---
EXPOSE 7860

# --- Launch FastAPI server ---
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
