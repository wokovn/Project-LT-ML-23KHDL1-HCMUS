#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv_phase1" ]]; then
  echo "ERROR: .venv_phase1 not found"
  exit 1
fi

source .venv_phase1/bin/activate

TEST_CSV="data/xtts_stage2_24k_mono/test_wav.csv"
DATA_ROOT="data/xtts_stage2_24k_mono"
EVAL_ROOT="runs/vieneu_tts/20260420_testset_eval_best3"

mkdir -p "$EVAL_ROOT"

# Ensure tokenizer files exist inside best checkpoints.
copy_tokenizer_assets() {
  local src_final="$1"
  local dst_best="$2"
  for f in added_tokens.json merges.txt special_tokens_map.json tokenizer.json tokenizer_config.json vocab.json; do
    if [[ -f "$src_final/$f" ]]; then
      cp -f "$src_final/$f" "$dst_best/$f"
    fi
  done
}

copy_tokenizer_assets \
  "runs/vieneu_tts/20260419_vieneu_transcript_phase1_full/phase1/checkpoints/final" \
  "runs/vieneu_tts/20260419_vieneu_transcript_phase1_full/phase1/checkpoints/checkpoint-8000"

copy_tokenizer_assets \
  "runs/vieneu_tts/20260419_vieneu_transcript_phase2_full/phase2/checkpoints/final" \
  "runs/vieneu_tts/20260419_vieneu_transcript_phase2_full/phase2/checkpoints/checkpoint-15500"

copy_tokenizer_assets \
  "runs/vieneu_tts/20260420_vieneu_transcript_phase3_refine_retry1/phase3/checkpoints/final" \
  "runs/vieneu_tts/20260420_vieneu_transcript_phase3_refine_retry1/phase3/checkpoints/checkpoint-17000"

run_phase_eval() {
  local phase_name="$1"
  local ckpt_path="$2"

  local phase_dir="$EVAL_ROOT/$phase_name"
  local gen_dir="$phase_dir/generated"
  local manifest_csv="$phase_dir/manifest.csv"
  local errors_csv="$phase_dir/manifest_errors.csv"
  local metrics_json="$phase_dir/metrics_summary.json"
  local metrics_csv="$phase_dir/metrics_summary_per_utt.csv"

  mkdir -p "$phase_dir"

  echo "=============================="
  echo "Running $phase_name"
  echo "checkpoint=$ckpt_path"

  python models/VieNeu-TTS/templates/scripts/infer_testset_vieneu_standard.py \
    --backbone-repo "$ckpt_path" \
    --test-csv "$TEST_CSV" \
    --data-root "$DATA_ROOT" \
    --output-dir "$gen_dir" \
    --manifest-out "$manifest_csv" \
    --errors-out "$errors_csv" \
    --speaker-col speaker_name \
    --batch-size 16 \
    --max-chars 256 \
    --skip-existing

  python models/VieNeu-TTS/templates/scripts/evaluate_wer_mcd.py \
    --test-csv "$TEST_CSV" \
    --generated-dir "$gen_dir" \
    --data-root "$DATA_ROOT" \
    --sample-rate 24000 \
    --n-mfcc 14 \
    --n-fft 1024 \
    --hop-length 480 \
    --max-frames-mfcc 1200 \
    --max-frames-f0 1600 \
    --f0-min-hz 50 \
    --f0-max-hz 550 \
    --output-json "$metrics_json" \
    --output-csv "$metrics_csv"

  echo "done_phase=$phase_name"
  echo "metrics_json=$metrics_json"
}

run_phase_eval \
  "phase1_best" \
  "runs/vieneu_tts/20260419_vieneu_transcript_phase1_full/phase1/checkpoints/checkpoint-8000"

run_phase_eval \
  "phase2_best" \
  "runs/vieneu_tts/20260419_vieneu_transcript_phase2_full/phase2/checkpoints/checkpoint-15500"

run_phase_eval \
  "phase3_best" \
  "runs/vieneu_tts/20260420_vieneu_transcript_phase3_refine_retry1/phase3/checkpoints/checkpoint-17000"

python - <<'PY'
import json
from pathlib import Path

root = Path("runs/vieneu_tts/20260420_testset_eval_best3")
summary = {}
for phase in ["phase1_best", "phase2_best", "phase3_best"]:
    p = root / phase / "metrics_summary.json"
    summary[phase] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

out = root / "all_phases_metrics_summary.json"
out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"all_summary={out}")
PY

python models/VieNeu-TTS/templates/scripts/update_report_test_metrics.py \
  --summary-json "$EVAL_ROOT/all_phases_metrics_summary.json" \
  --report-md models/VieNeu-TTS/VIE_NEU_TTS_REPORT_FULL.md

echo "All phase evaluations completed."
