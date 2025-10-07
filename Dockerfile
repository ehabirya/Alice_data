# ===== Meshroom Headless API (runtime download) =====
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# System deps (Meshroom runtime + GLB export + Python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates curl zip \
    libgl1-mesa-glx libglu1-mesa libxrandr2 libxinerama1 libxi6 libxrender1 \
    libxxf86vm1 libxkbcommon0 libjpeg-turbo8 libpng16-16 libtiff5 ffmpeg \
    python3 python3-pip python3-venv \
    assimp-utils \
 && rm -rf /var/lib/apt/lists/*

# Python deps
RUN python3 -m pip install --no-cache-dir fastapi uvicorn[standard] pillow

# App code
WORKDIR /app
COPY server.py /app/server.py
COPY utils.py  /app/utils.py
COPY start.sh  /app/start.sh
RUN chmod +x /app/start.sh

# Work dirs
RUN mkdir -p /data/work /data/out /opt/meshroom
ENV PATH="/opt/meshroom:${PATH}"

# Expose API port
EXPOSE 7860

# Start
CMD ["/app/start.sh"]
