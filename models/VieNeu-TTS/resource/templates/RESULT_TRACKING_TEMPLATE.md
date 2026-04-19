# Result Tracking Template (copy into report)

## 1) Run metadata

| Run ID | Phase | Date | Git commit | Seed | Device | Notes |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## 2) Hyperparameter record

| Run ID | LR | Batch size | Grad accum | Precision | Freeze modules | Scheduler | Early stopping patience |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## 3) Epoch tracking (for learning curve)

| Run ID | Epoch | Train loss | Val loss | Best val so far | Checkpoint saved | Audio sample saved | Comment |
|---|---|---:|---:|---:|---|---|---|
|  |  |  |  |  |  |  |  |

## 4) Phase summary

| Phase | Start checkpoint | End checkpoint | Best checkpoint | Best val loss | Stop reason |
|---|---|---|---|---:|---|
| Phase 1 (warmup) |  |  |  |  |  |
| Phase 2 (full finetune) |  |  |  |  |  |
| Phase 3 (refine) |  |  |  |  |  |

## 5) Test-set metrics (for report section 5.2)

| Model/checkpoint | MCD (lower better) | WER (lower better) | CER (lower better) | MOS mean (1-5) | MOS std |
|---|---:|---:|---:|---:|---:|
| Baseline (original) |  |  |  |  |  |
| Fine-tuned (best) |  |  |  |  |  |

## 6) Ablation table (for report section 5.3)

| Setup | Data size | Text normalization | Trim silence | MCD | WER | CER | MOS |
|---|---:|---|---|---:|---:|---:|---:|
| Baseline original | 100% | N/A | N/A |  |  |  |  |
| Full pipeline | 100% | Yes | Yes |  |  |  |  |
| No text normalization | 100% | No | Yes |  |  |  |  |
| No trim silence | 100% | Yes | No |  |  |  |  |
| Reduced data | 50% | Yes | Yes |  |  |  |  |

## 7) Error analysis sample log (for report section 6.2)

| Audio ID | Ground truth text | Generated behavior | Error type | Hypothesis | Proposed fix |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 8) Final model selection note

- Selected checkpoint:
- Why selected:
- Trade-off observed:
- Ready for deployment: Yes/No
