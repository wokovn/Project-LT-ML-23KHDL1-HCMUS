# vnTTS FastAPI (GPU)

This folder provides a FastAPI service that loads `anhnh2002/vnTTS` and exposes:

- `POST /v1/tts` for synchronous TTS inference.
- `POST /v1/tasks/tts` and `GET /v1/tasks/{task_id}` for async task dispatch.
- `GET /health` for runtime health checks.

## 1) Prepare environment (Windows + GPU)

Use Python 3.11 and run from repository root:

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv311\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
.\.venv311\Scripts\python.exe -m pip install -r .\models\XTTSv2-Finetuning-for-New-Languages\requirements.txt
.\.venv311\Scripts\python.exe -m pip install -r .\backend\tts_fastapi\requirements.txt
```

## 2) Download model weights

```powershell
.\.venv311\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='anhnh2002/vnTTS', repo_type='model', local_dir='models/vntts-runtime-model')"
```

## 3) Run FastAPI service

```powershell
$env:PYTHONPATH="e:/Users/Admin/Documents/GitHub/Project-LT-ML-23KHDL1-HCMUS/models/XTTSv2-Finetuning-for-New-Languages"
$env:VNTTS_MODEL_DIR="e:/Users/Admin/Documents/GitHub/Project-LT-ML-23KHDL1-HCMUS/models/vntts-runtime-model"
$env:VNTTS_DEVICE="cuda:0"
.\.venv311\Scripts\python.exe -m uvicorn backend.tts_fastapi.app:app --host 127.0.0.1 --port 8001
```

## 4) Smoke test

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/v1/tts -ContentType "application/json" -Body '{"text":"Xin chao ban, day la ban thu am tu vnTTS.","language":"vi"}'
```

The API returns a JSON payload containing `audio_base64` and `sample_rate`.
