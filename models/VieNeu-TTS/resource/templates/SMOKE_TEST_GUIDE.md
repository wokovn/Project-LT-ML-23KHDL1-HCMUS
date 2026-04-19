# Smoke Test Guide (for Stage 2 + quick train check)

## Why Stage 2 is still needed even if dataset is already normalized

Global dataset normalization is not enough. VieNeu-TTS can still require model-specific alignment so that data matches training config exactly.

Examples:
- Sample rate must match config (for example 24000 Hz).
- Channel count must be mono.
- Silence trimming aggressiveness may need adjustment to avoid unnatural pauses.
- Text normalization rules should match tokenizer behavior used in training.
- Duration limits and filtering should match model/runtime constraints.

So Stage 2 is not "do it again for no reason". It is the compatibility layer between dataset and this exact model/config.

## Step A - Run model-specific dataset alignment smoke check

```bash
python models/VieNeu-TTS/resource/templates/scripts/smoke_test_dataset_alignment.py \
  --data-root data/xtts \
  --csv data/xtts/train_wav.csv \
  --csv data/xtts/eval.csv \
  --expected-sr 24000 \
  --expected-channels 1 \
  --max-samples 256 \
  --fail-on-warning
```

If this command fails, fix data issues before training.

## Step B - Create tiny smoke subsets (deterministic)

```bash
python models/VieNeu-TTS/resource/templates/scripts/create_smoke_subset.py \
  --train-csv data/xtts/train_wav.csv \
  --eval-csv data/xtts/eval.csv \
  --output-dir data/xtts/smoke \
  --train-n 64 \
  --eval-n 16 \
  --seed 20260419
```

Outputs:
- data/xtts/smoke/train_smoke.csv
- data/xtts/smoke/eval_smoke.csv

## Step C - Run quick Phase 1 smoke train

Use your training script and point it to smoke subset CSVs.

Example template:

```bash
PYTHON_BIN=python \
TRAIN_SCRIPT=train_xtts.py \
CONFIG=models/VieNeu-TTS/resource/templates/train_config_3phase.yaml \
OUT_DIR=runs/vieneu_tts/smoke_phase1 \
EXTRA_ARGS="--train-csv data/xtts/smoke/train_smoke.csv --eval-csv data/xtts/smoke/eval_smoke.csv --max-steps 100 --epochs 1" \
./models/VieNeu-TTS/resource/templates/scripts/run_phase1_warmup.sh
```

## Step D - Pass criteria for smoke test

- Train starts and runs without shape mismatch errors.
- Train/val loss are logged.
- At least one checkpoint is saved.
- Optimizer state is saved.
- At least one sample audio is generated.
- Audio is intelligible (not silent, not heavy noise, no severe truncation).

If all pass, move to full Phase 1 on full train/eval splits.
