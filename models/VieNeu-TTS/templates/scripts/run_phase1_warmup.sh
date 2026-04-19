#!/usr/bin/env bash
set -euo pipefail

# Replace TRAIN_SCRIPT with your actual training entry point.
PYTHON_BIN="${PYTHON_BIN:-python}"
TRAIN_SCRIPT="${TRAIN_SCRIPT:-train_xtts.py}"
CONFIG="${CONFIG:-models/VieNeu-TTS/templates/train_config_3phase.yaml}"
RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${OUT_DIR:-runs/vieneu_tts/${RUN_TAG}/phase1}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

${PYTHON_BIN} "${TRAIN_SCRIPT}" \
  --config "${CONFIG}" \
  --phase phase1 \
  --output-dir "${OUT_DIR}" \
  --seed 20260419 \
  --mixed-precision fp16 \
  --save-top-k 3 \
  --save-last true \
  ${EXTRA_ARGS}

echo "Phase 1 done. Output: ${OUT_DIR}"
