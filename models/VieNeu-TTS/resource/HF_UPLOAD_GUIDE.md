# Publish Best Models to Hugging Face

GitHub regular repositories reject large model files (`model.safetensors` is > 100MB).
Use Hugging Face Hub for model weights and keep this GitHub repo for code/report/sample audio.

## 1) Install and login

```bash
pip install -U huggingface_hub
huggingface-cli login
```

## 2) Prepare three best inference bundles

From repository root:

```bash
python models/VieNeu-TTS/templates/scripts/prepare_best_models_for_hf.py \
  --output-root models/VieNeu-TTS/resource/hf_best_models
```

Output folders:

- `models/VieNeu-TTS/resource/hf_best_models/phase1_best`
- `models/VieNeu-TTS/resource/hf_best_models/phase2_best`
- `models/VieNeu-TTS/resource/hf_best_models/phase3_best`

## 3) Create a HF model repo

Choose your HF namespace and repo name (example: `YOUR_HF_USER/vieneu-tts-best3`).

```bash
huggingface-cli repo create vieneu-tts-best3 --type model
```

## 4) Upload all three phase bundles

```bash
huggingface-cli upload YOUR_HF_USER/vieneu-tts-best3 \
  models/VieNeu-TTS/resource/hf_best_models/phase1_best phase1_best

huggingface-cli upload YOUR_HF_USER/vieneu-tts-best3 \
  models/VieNeu-TTS/resource/hf_best_models/phase2_best phase2_best

huggingface-cli upload YOUR_HF_USER/vieneu-tts-best3 \
  models/VieNeu-TTS/resource/hf_best_models/phase3_best phase3_best

huggingface-cli upload YOUR_HF_USER/vieneu-tts-best3 \
  models/VieNeu-TTS/resource/hf_best_models/hf_bundle_manifest.json hf_bundle_manifest.json
```

## 5) Recommended README in HF repo

Include:

- Training summary and run IDs.
- Which checkpoint is recommended for inference (`phase3_best`).
- Required inference dependencies.
- Citation and license notes.
