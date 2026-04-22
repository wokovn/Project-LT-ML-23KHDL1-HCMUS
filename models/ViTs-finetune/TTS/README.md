# README (local changes)

Purpose: This file lists what I changed/added. Use it to recreate a folder identical to my custom code from the upstream repo.

## Upstream repo

- https://github.com/coqui-ai/TTS

## How to recreate this folder (from upstream)

1. Clone the upstream repo:
   git clone https://github.com/coqui-ai/TTS
2. Copy/overwrite the files listed below from my modified set into the cloned repo (keep the same paths).

## Summary of changes

- Added pitch contour loss for VITS (pitch predictor + loss)
- Added F0 cache and lazy F0, plus new options: pitch_loss_alpha and f0_cache_path
- Updated F0 extraction to prefer pyworld if available, with pyin fallback
- Switched audio loader to soundfile
- Added Vietnamese VITS recipe and scripts (train, benchmark, evaluate)
- Fixed sampler init for newer PyTorch
- Synced phoneme aliases "vi" and "vi-vn"

## Modified files

- TTS\tts\configs\vits_config.py
- TTS\tts\datasets\dataset.py
- TTS\tts\layers\losses.py
- TTS\tts\models\vits.py
- TTS\tts\utils\text\phonemizers\init.py
- TTS\utils\audio\numpy_transforms.py
- TTS\utils\samplers.py

## New files

- recipes\vietnamese\vits\train_vits_vi.py
- recipes\vietnamese\vits\benchmark_inference.py
- recipes\vietnamese\vits\evaluate.py

## Quick notes

- Pitch loss is active only when pitch_loss_alpha > 0 and compute_f0 = True.
- Enable lazy F0 via TTS_LAZY_F0=1 or --lazy-f0 in the Vietnamese recipe.
- If pitch_stats.npy is missing, F0 normalization is skipped (training uses raw F0).
