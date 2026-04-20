#!/usr/bin/env bash
set -euo pipefail

# Setup script for a rented Linux machine with RTX 3090 (24GB).
# This script creates a local venv and installs training dependencies for Phase 1.

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
VENV_DIR="${VENV_DIR:-.venv}"
TORCH_VERSION="${TORCH_VERSION:-2.6.0}"
TORCHAUDIO_VERSION="${TORCHAUDIO_VERSION:-2.6.0}"
TORCH_CUDA_TAG="${TORCH_CUDA_TAG:-cu124}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/${TORCH_CUDA_TAG}}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "ERROR: ${PYTHON_BIN} was not found. Install Python 3.11 first."
  exit 1
fi

if [ ! -d "${VENV_DIR}" ]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip setuptools wheel

# Install GPU stack first so later packages resolve against installed torch.
pip install \
  "torch==${TORCH_VERSION}+${TORCH_CUDA_TAG}" \
  "torchaudio==${TORCHAUDIO_VERSION}+${TORCH_CUDA_TAG}" \
  --index-url "${TORCH_INDEX_URL}"

pip install -r models/VieNeu-TTS/requirements-train.txt

python - <<'PY'
import sys
import torch

print('python:', sys.version)
print('torch:', torch.__version__)
print('cuda_available:', torch.cuda.is_available())
print('cuda_version:', torch.version.cuda)
print('gpu_count:', torch.cuda.device_count())
if torch.cuda.is_available():
    print('gpu_name:', torch.cuda.get_device_name(0))
PY

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi
fi

echo "Setup complete. Activate with: source ${VENV_DIR}/bin/activate"
