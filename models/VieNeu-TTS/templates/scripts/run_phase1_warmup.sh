#!/usr/bin/env bash
set -euo pipefail

# Replace TRAIN_SCRIPT with your actual training entry point.
PYTHON_BIN="${PYTHON_BIN:-python}"
TRAIN_SCRIPT="${TRAIN_SCRIPT:-train_xtts.py}"
CONFIG="${CONFIG:-models/VieNeu-TTS/templates/train_config_3phase.yaml}"
RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${OUT_DIR:-runs/vieneu_tts/${RUN_TAG}/phase1}"
EXTRA_ARGS="${EXTRA_ARGS:-}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
ENV_MANIFEST_FILE="${ENV_MANIFEST_FILE:-env_manifest.txt}"

CKPT_DIR="${OUT_DIR}/checkpoints"
LOG_DIR="${OUT_DIR}/logs"
SAMPLE_DIR="${OUT_DIR}/samples"
METRIC_DIR="${OUT_DIR}/metrics"
HANDOFF_DIR="${OUT_DIR}/handoff_phase2"

if [ ! -f "${TRAIN_SCRIPT}" ]; then
  echo "ERROR: TRAIN_SCRIPT not found: ${TRAIN_SCRIPT}"
  echo "Set TRAIN_SCRIPT to your real training entrypoint before running phase 1."
  exit 1
fi

if [ ! -f "${CONFIG}" ]; then
  echo "ERROR: CONFIG not found: ${CONFIG}"
  exit 1
fi

mkdir -p "${CKPT_DIR}" "${LOG_DIR}" "${SAMPLE_DIR}" "${METRIC_DIR}" "${HANDOFF_DIR}"

if [ -f "${CONFIG}" ]; then
  cp "${CONFIG}" "${HANDOFF_DIR}/phase1_config_snapshot.yaml"
fi

cat > "${HANDOFF_DIR}/phase2_next_steps.md" <<EOF
# Phase 1 -> Phase 2 Handoff

## 1) Output cần có sau khi Phase 1 kết thúc
- Checkpoint tốt nhất theo val_loss.
- Checkpoint epoch cuối.
- Log train/val loss theo step/epoch.
- Audio samples từ fixed sentences.

## 2) Việc cần làm ngay sau Phase 1
1. Chọn BEST_PHASE1_CKPT từ top-k checkpoints + nghe mẫu audio.
2. Ghi nhận overfit/underfit ban đầu từ đường loss.
3. Chốt thay đổi hyperparameter cho Phase 2 (nếu cần).

## 3) Cách chạy tiếp Phase 2
PHASE1_CKPT=<PATH_TO_BEST_PHASE1_CKPT> \
bash models/VieNeu-TTS/templates/scripts/run_phase2_full_finetune.sh

## 4) Tài sản chuyển tiếp cho Phase 2
- BEST_PHASE1_CKPT
- phase1_config_snapshot.yaml
- Bảng nhận xét lỗi phát âm/ngắt nghỉ từ audio samples
EOF

{
  echo "timestamp=$(date -Iseconds)"
  echo "run_tag=${RUN_TAG}"
  echo "cuda_visible_devices=${CUDA_VISIBLE_DEVICES}"
  echo "python_bin=${PYTHON_BIN}"
  echo "train_script=${TRAIN_SCRIPT}"
  echo "config=${CONFIG}"
  echo "---- python ----"
  "${PYTHON_BIN}" --version
  echo "---- torch/cuda ----"
  "${PYTHON_BIN}" - <<'PY'
import platform
import torch

print("platform:", platform.platform())
print("torch:", torch.__version__)
print("cuda_available:", torch.cuda.is_available())
print("cuda_version:", torch.version.cuda)
print("gpu_count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("gpu_0:", torch.cuda.get_device_name(0))
PY
  if command -v nvidia-smi >/dev/null 2>&1; then
    echo "---- nvidia-smi ----"
    nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv,noheader
  fi
} > "${METRIC_DIR}/${ENV_MANIFEST_FILE}" 2>&1 || true

export CUDA_VISIBLE_DEVICES
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-max_split_size_mb:128,expandable_segments:True}"

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
echo "Phase 1 handoff note: ${HANDOFF_DIR}/phase2_next_steps.md"
