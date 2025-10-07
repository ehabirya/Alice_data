#!/usr/bin/env bash
set -euo pipefail

# --- Config (env-driven) ---
HF_FILE_URL="${HF_FILE_URL:-https://huggingface.co/datasets/ericos1234/alice_data/resolve/main/Meshroom-2023.3.0-linux.tar.gz}"
FALLBACK_URL="${FALLBACK_URL:-https://github.com/alicevision/meshroom/releases/download/v2023.3.0/Meshroom-2023.3.0-linux.tar.gz}"
CACHE_DIR="${MESHROOM_DIR:-/opt/meshroom}"

echo "Meshroom dir      : ${CACHE_DIR}"
echo "HF_FILE_URL       : ${HF_FILE_URL}"
echo "Using fallback    : ${FALLBACK_URL}"

mkdir -p "${CACHE_DIR}"

# Download Meshroom only if not present
if [[ ! -x "${CACHE_DIR}/meshroom_photogrammetry" ]]; then
  echo "Meshroom not found. Downloading…"

  TMP=/tmp/meshroom.tar.gz
  rm -f "$TMP"

  if [[ -n "${HF_TOKEN:-}" ]]; then
    echo "Downloading from HF with token…"
    if ! curl -fL --retry 5 --retry-delay 2 -H "Authorization: Bearer ${HF_TOKEN}" -o "$TMP" "$HF_FILE_URL"; then
      echo "HF download failed, trying fallback…"
      curl -fL --retry 5 --retry-delay 2 -o "$TMP" "$FALLBACK_URL"
    fi
  else
    echo "Downloading from HF (public)…"
    if ! curl -fL --retry 5 --retry-delay 2 -o "$TMP" "$HF_FILE_URL"; then
      echo "HF download failed, trying fallback…"
      curl -fL --retry 5 --retry-delay 2 -o "$TMP" "$FALLBACK_URL"
    fi
  fi

  echo "Extracting to ${CACHE_DIR}…"
  tar -xzf "$TMP" -C "$CACHE_DIR" --strip-components=1
  rm -f "$TMP"
else
  echo "Meshroom already present. Skipping download."
fi

# Ensure Meshroom is on PATH for this process
export PATH="${CACHE_DIR}:${PATH}"

# Launch API
exec uvicorn server:app --host 0.0.0.0 --port "${PORT:-7860}"
