#!/usr/bin/env bash
set -euo pipefail

# Launch Phase 1 in tmux for rented-machine stability.
# Required variables:
#   TRAIN_SCRIPT: absolute or repo-relative path to the real training entrypoint.
# Optional variables:
#   SESSION, RUN_TAG, CONFIG, OUT_DIR, PYTHON_BIN, EXTRA_ARGS

SESSION="${SESSION:-vieneu_phase1}"
RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)_phase1}"
CONFIG="${CONFIG:-models/VieNeu-TTS/templates/train_config_3phase_rtx3090.yaml}"
OUT_DIR="${OUT_DIR:-runs/vieneu_tts/${RUN_TAG}/phase1}"
PYTHON_BIN="${PYTHON_BIN:-python}"
TRAIN_SCRIPT="${TRAIN_SCRIPT:-}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

if [ -z "${TRAIN_SCRIPT}" ]; then
  echo "ERROR: TRAIN_SCRIPT is required."
  echo "Example: TRAIN_SCRIPT=src/train_xtts.py bash models/VieNeu-TTS/templates/scripts/run_phase1_3090_tmux.sh"
  exit 1
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "ERROR: tmux not found. Install tmux first (sudo apt install -y tmux)."
  exit 1
fi

mkdir -p "$(dirname "${OUT_DIR}")"

CMD="RUN_TAG='${RUN_TAG}' OUT_DIR='${OUT_DIR}' PYTHON_BIN='${PYTHON_BIN}' TRAIN_SCRIPT='${TRAIN_SCRIPT}' CONFIG='${CONFIG}' EXTRA_ARGS='${EXTRA_ARGS}' bash models/VieNeu-TTS/templates/scripts/run_phase1_warmup.sh | tee '${OUT_DIR%/phase1}/phase1_train.log'"

if tmux has-session -t "${SESSION}" 2>/dev/null; then
  echo "ERROR: tmux session already exists: ${SESSION}"
  echo "Attach with: tmux attach -t ${SESSION}"
  exit 1
fi

tmux new-session -d -s "${SESSION}" "${CMD}"

echo "Phase 1 started in tmux session: ${SESSION}"
echo "Attach: tmux attach -t ${SESSION}"
echo "Detach: Ctrl+B then D"
echo "Output dir: ${OUT_DIR}"
