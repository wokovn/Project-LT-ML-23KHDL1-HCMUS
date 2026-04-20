import base64
import io
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, Literal, Optional, Tuple

import soundfile as sf
import torch
from fastapi import BackgroundTasks, FastAPI, HTTPException
from huggingface_hub import snapshot_download
from num2words import num2words
from pydantic import BaseModel, Field
from underthesea import sent_tokenize, text_normalize
from vinorm import TTSnorm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
XTTS_REPO_PATH = Path(
    os.getenv(
        "XTTS_REPO_PATH",
        str(PROJECT_ROOT / "models" / "XTTSv2-Finetuning-for-New-Languages"),
    )
)

if str(XTTS_REPO_PATH) not in sys.path:
    sys.path.insert(0, str(XTTS_REPO_PATH))

from TTS.tts.configs.xtts_config import XttsConfig  # noqa: E402
from TTS.tts.models.xtts import Xtts  # noqa: E402

MODEL_REPO_ID = os.getenv("VNTTS_MODEL_REPO_ID", "anhnh2002/vnTTS")
MODEL_DIR = Path(
    os.getenv("VNTTS_MODEL_DIR", str(PROJECT_ROOT / "models" / "vntts-runtime-model"))
)
DEFAULT_SPEAKER = os.getenv("VNTTS_DEFAULT_SPEAKER", "vi_man.wav")
DEVICE = os.getenv("VNTTS_DEVICE", "cuda:0" if torch.cuda.is_available() else "cpu")
MAX_TASKS = int(os.getenv("VNTTS_MAX_TASKS", "100"))
SAMPLE_RATE = int(os.getenv("VNTTS_SAMPLE_RATE", "24000"))
DISABLE_VINORM = os.getenv("VNTTS_DISABLE_VINORM", "false").lower() in {"1", "true", "yes"}
CHUNK_MAX_WORDS = int(os.getenv("VNTTS_CHUNK_MAX_WORDS", "30"))
CHUNK_MIN_WORDS = int(os.getenv("VNTTS_CHUNK_MIN_WORDS", "15"))
CHUNK_CROSSFADE_MS = int(os.getenv("VNTTS_CHUNK_CROSSFADE_MS", "35"))

LOGGER = logging.getLogger("vntts-fastapi")
_VINORM_FALLBACK_WARNED = False

COMMON_ASCII_VI_TOKENS = {
    "ngay": "ngày",
    "luc": "lúc",
    "gia": "giá",
    "tang": "tăng",
    "giam": "giảm",
    "voi": "với",
    "hom": "hôm",
    "gio": "giờ",
    "phut": "phút",
    "dong": "đồng",
    "phan": "phần",
    "tram": "trăm",
}

ROMAN_NUMERAL_VALUES = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}

TaskStatus = Literal["queued", "running", "completed", "failed"]


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language: str = Field(default="vi")
    speaker_audio: Optional[str] = None


class TtsResponse(BaseModel):
    sample_rate: int
    audio_base64: str
    chunks: int
    device: str


class TaskCreatedResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: float
    updated_at: float
    error: Optional[str] = None
    result: Optional[TtsResponse] = None


@dataclass
class TaskRecord:
    status: TaskStatus
    created_at: float
    updated_at: float
    error: Optional[str] = None
    result: Optional[dict] = None


def _int_to_vi_words(raw: str) -> str:
    digits = raw.replace(".", "").replace(",", "")
    if not digits.isdigit():
        return raw

    try:
        return num2words(int(digits), lang="vi")
    except Exception:
        return raw


def _decimal_to_vi_words(raw: str) -> str:
    if "," in raw:
        parts = raw.split(",")
    elif "." in raw:
        parts = raw.split(".")
    else:
        return _int_to_vi_words(raw)

    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return raw

    left = _int_to_vi_words(parts[0])
    right = " ".join(_int_to_vi_words(digit) for digit in parts[1])
    return f"{left} phẩy {right}"


def _number_token_to_vi(raw: str) -> str:
    token = re.sub(r"\s+", "", raw)

    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", token):
        return _int_to_vi_words(token)

    if re.fullmatch(r"\d+[.,]\d+", token):
        return _decimal_to_vi_words(token)

    if token.isdigit():
        return _int_to_vi_words(token)

    return raw


def _roman_to_int(token: str) -> Optional[int]:
    roman = token.upper()
    if not re.fullmatch(r"M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", roman):
        return None

    total = 0
    i = 0
    while i < len(roman):
        current = ROMAN_NUMERAL_VALUES[roman[i]]
        if i + 1 < len(roman):
            nxt = ROMAN_NUMERAL_VALUES[roman[i + 1]]
            if nxt > current:
                total += nxt - current
                i += 2
                continue

        total += current
        i += 1

    return total if total > 0 else None


def _normalize_vi_custom_tokens(text: str) -> str:
    normalized = text

    def contextual_roman_repl(match: re.Match[str]) -> str:
        prefix = match.group(1)
        roman = match.group(2)
        value = _roman_to_int(roman)
        if value is None:
            return match.group(0)
        return f"{prefix} {_int_to_vi_words(str(value))}"

    normalized = re.sub(
        r"\b(chương|phần|mục|quý|thế kỷ|đợt|lần|tập|kỳ)\s+([IVXLCDMivxlcdm]+)\b",
        contextual_roman_repl,
        normalized,
        flags=re.IGNORECASE,
    )

    def standalone_roman_repl(match: re.Match[str]) -> str:
        roman = match.group(0)
        value = _roman_to_int(roman)
        if value is None:
            return roman
        return _int_to_vi_words(str(value))

    normalized = re.sub(r"\b[IVXLCDM]{2,}\b", standalone_roman_repl, normalized)

    # Read acronym AI as separate letters for more natural TTS pronunciation.
    normalized = re.sub(r"\bA[.]?I\b", "A I", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _match_case(word: str, replacement: str) -> str:
    if word.isupper():
        return replacement.upper()
    if word[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _accentize_common_vi_ascii_tokens(text: str) -> str:
    updated = text
    for ascii_word, vi_word in COMMON_ASCII_VI_TOKENS.items():
        pattern = rf"\b{re.escape(ascii_word)}\b"
        updated = re.sub(
            pattern,
            lambda m: _match_case(m.group(0), vi_word),
            updated,
            flags=re.IGNORECASE,
        )
    return updated


def _normalize_vi_text_fallback(text: str) -> str:
    normalized = text_normalize(text)
    normalized = _accentize_common_vi_ascii_tokens(normalized)

    def date_repl(match: re.Match[str]) -> str:
        day, month, year = match.group(1), match.group(2), match.group(3)
        return (
            f"ngày {_int_to_vi_words(day)} "
            f"tháng {_int_to_vi_words(month)} "
            f"năm {_int_to_vi_words(year)}"
        )

    normalized = re.sub(
        r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{2,4})\b",
        date_repl,
        normalized,
    )

    def time_repl(match: re.Match[str]) -> str:
        hour, minute = match.group(1), match.group(2)
        return f"{_int_to_vi_words(hour)} giờ {_int_to_vi_words(minute)} phút"

    normalized = re.sub(r"\b(\d{1,2})\s*:\s*(\d{2})\b", time_repl, normalized)

    normalized = re.sub(
        r"\b(\d+(?:\s*[.,]\s*\d+)?)\s*%",
        lambda m: f"{_number_token_to_vi(m.group(1))} phần trăm",
        normalized,
    )

    normalized = re.sub(
        r"\b(\d+(?:\s*[.,]\s*\d+)*)\s*(?:đ|d|đồng|dong|vnd|VND)\b",
        lambda m: f"{_number_token_to_vi(m.group(1))} đồng",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        r"\b\d+\s*[.,]\s*\d+\b",
        lambda m: _number_token_to_vi(m.group(0)),
        normalized,
    )

    normalized = re.sub(
        r"\b\d{1,3}(?:\s*[.,]\s*\d{3})*\b",
        lambda m: _number_token_to_vi(m.group(0)),
        normalized,
    )

    normalized = re.sub(
        r"\b(ngày|tháng|năm|giờ|phút)\s+\1\b",
        r"\1",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def preprocess_text(text: str, language: str = "vi") -> list[str]:
    if language == "vi":
        global _VINORM_FALLBACK_WARNED
        if not DISABLE_VINORM:
            try:
                text = TTSnorm(text, unknown=False, lower=False, rule=True)
            except OSError as exc:
                # vinorm spawns an external process that may be incompatible on Windows.
                if getattr(exc, "winerror", None) == 193 or "WinError 193" in str(exc):
                    if not _VINORM_FALLBACK_WARNED:
                        LOGGER.warning(
                            "vinorm normalization is not compatible on this environment; using rule-based fallback"
                        )
                        _VINORM_FALLBACK_WARNED = True
                    text = _normalize_vi_text_fallback(text)
                else:
                    raise
            except UnicodeEncodeError:
                if not _VINORM_FALLBACK_WARNED:
                    LOGGER.warning(
                        "vinorm normalization cannot encode current text on this environment; using rule-based fallback"
                    )
                    _VINORM_FALLBACK_WARNED = True
                text = _normalize_vi_text_fallback(text)
            except Exception:
                if not _VINORM_FALLBACK_WARNED:
                    LOGGER.warning(
                        "vinorm normalization failed unexpectedly; using rule-based fallback"
                    )
                    _VINORM_FALLBACK_WARNED = True
                text = _normalize_vi_text_fallback(text)
        else:
            text = _normalize_vi_text_fallback(text)

        text = _normalize_vi_custom_tokens(text)

    if language in ["ja", "zh-cn"]:
        sentences = text.split("。")
    else:
        sentences = sent_tokenize(text)

    chunks: list[str] = []
    chunk_i = ""
    len_chunk_i = 0

    for sentence in sentences:
        chunk_i += " " + sentence
        len_chunk_i += len(sentence.split())

        if len_chunk_i >= CHUNK_MAX_WORDS:
            chunks.append(chunk_i.strip())
            chunk_i = ""
            len_chunk_i = 0

    if chunk_i.strip():
        if chunks and len_chunk_i < CHUNK_MIN_WORDS:
            chunks[-1] += " " + chunk_i.strip()
        else:
            chunks.append(chunk_i.strip())

    return chunks


def merge_wav_chunks(wav_chunks: list[torch.Tensor], sample_rate: int) -> torch.Tensor:
    if len(wav_chunks) == 1:
        return wav_chunks[0].float()

    crossfade_samples = max(0, int(sample_rate * CHUNK_CROSSFADE_MS / 1000))
    merged = wav_chunks[0].float()

    for wav_chunk in wav_chunks[1:]:
        next_chunk = wav_chunk.float()

        if crossfade_samples <= 0:
            merged = torch.cat((merged, next_chunk), dim=0)
            continue

        # Keep enough signal in each side to avoid over-trimming short chunks.
        overlap = min(crossfade_samples, merged.numel() // 4, next_chunk.numel() // 4)
        if overlap <= 0:
            merged = torch.cat((merged, next_chunk), dim=0)
            continue

        fade_out = torch.linspace(1.0, 0.0, steps=overlap, dtype=merged.dtype)
        fade_in = torch.linspace(0.0, 1.0, steps=overlap, dtype=next_chunk.dtype)
        crossfaded = (merged[-overlap:] * fade_out) + (next_chunk[:overlap] * fade_in)

        merged = torch.cat((merged[:-overlap], crossfaded, next_chunk[overlap:]), dim=0)

    return merged


class VnTTSRuntime:
    def __init__(self, model_repo_id: str, model_dir: Path, device: str):
        self.model_repo_id = model_repo_id
        self.model_dir = model_dir
        self.device = device
        self.model: Optional[Xtts] = None
        self.config: Optional[XttsConfig] = None
        self._init_lock = Lock()
        self._inference_lock = Lock()
        self._speaker_cache: Dict[str, Tuple[torch.Tensor, torch.Tensor]] = {}

    def is_loaded(self) -> bool:
        return self.model is not None

    def _ensure_model_files(self) -> None:
        required = [
            self.model_dir / "model.pth",
            self.model_dir / "config.json",
            self.model_dir / "vocab.json",
            self.model_dir / DEFAULT_SPEAKER,
        ]
        if all(path.exists() for path in required):
            return

        self.model_dir.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=self.model_repo_id,
            repo_type="model",
            local_dir=str(self.model_dir),
        )

    def _load_model(self) -> None:
        if self.model is not None:
            return

        with self._init_lock:
            if self.model is not None:
                return

            self._ensure_model_files()

            config = XttsConfig()
            config.load_json(str(self.model_dir / "config.json"))

            model = Xtts.init_from_config(config)
            model.load_checkpoint(
                config,
                checkpoint_path=str(self.model_dir / "model.pth"),
                vocab_path=str(self.model_dir / "vocab.json"),
                use_deepspeed=False,
            )
            model.to(self.device)
            model.eval()

            self.config = config
            self.model = model

    def _resolve_speaker_path(self, speaker_audio: Optional[str]) -> Path:
        if not speaker_audio:
            speaker_path = self.model_dir / DEFAULT_SPEAKER
        else:
            candidate = Path(speaker_audio)
            speaker_path = candidate if candidate.is_absolute() else self.model_dir / candidate

        if not speaker_path.exists():
            raise ValueError(f"Speaker audio not found: {speaker_path}")

        return speaker_path

    def _get_speaker_latents(self, speaker_path: Path) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.model is None or self.config is None:
            raise RuntimeError("Model is not loaded")

        key = str(speaker_path.resolve())
        if key in self._speaker_cache:
            return self._speaker_cache[key]

        gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
            audio_path=key,
            gpt_cond_len=self.model.config.gpt_cond_len,
            max_ref_length=self.model.config.max_ref_len,
            sound_norm_refs=self.model.config.sound_norm_refs,
        )

        self._speaker_cache[key] = (gpt_cond_latent, speaker_embedding)
        return gpt_cond_latent, speaker_embedding

    def synthesize(self, request: TtsRequest) -> dict:
        self._load_model()

        if self.model is None:
            raise RuntimeError("Failed to initialize model")

        speaker_path = self._resolve_speaker_path(request.speaker_audio)

        with self._inference_lock:
            gpt_cond_latent, speaker_embedding = self._get_speaker_latents(speaker_path)
            chunks = preprocess_text(request.text, request.language)

            wav_chunks = []
            for text_chunk in chunks:
                if not text_chunk.strip():
                    continue

                wav_chunk = self.model.inference(
                    text=text_chunk,
                    language=request.language,
                    gpt_cond_latent=gpt_cond_latent,
                    speaker_embedding=speaker_embedding,
                    length_penalty=1.0,
                    repetition_penalty=10.0,
                    top_k=10,
                    top_p=0.5,
                )

                wav_chunks.append(torch.tensor(wav_chunk["wav"]))

            if not wav_chunks:
                raise ValueError("No audio chunk was generated")

            out_wav = merge_wav_chunks(wav_chunks, SAMPLE_RATE).unsqueeze(0).cpu().numpy()[0]

        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, out_wav, SAMPLE_RATE, format="WAV")
        audio_bytes = audio_buffer.getvalue()

        return {
            "sample_rate": SAMPLE_RATE,
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "chunks": len(wav_chunks),
            "device": self.device,
        }


runtime = VnTTSRuntime(model_repo_id=MODEL_REPO_ID, model_dir=MODEL_DIR, device=DEVICE)
app = FastAPI(title="vnTTS FastAPI", version="1.0.0")

_task_store: Dict[str, TaskRecord] = {}
_task_lock = Lock()


def _trim_tasks_locked() -> None:
    if len(_task_store) <= MAX_TASKS:
        return

    overflow = len(_task_store) - MAX_TASKS
    oldest_ids = sorted(_task_store.keys(), key=lambda item: _task_store[item].updated_at)[:overflow]
    for task_id in oldest_ids:
        _task_store.pop(task_id, None)


def _update_task(task_id: str, **kwargs) -> None:
    with _task_lock:
        task = _task_store.get(task_id)
        if task is None:
            return

        for key, value in kwargs.items():
            setattr(task, key, value)

        task.updated_at = time.time()


def _run_tts_task(task_id: str, payload: dict) -> None:
    _update_task(task_id, status="running", error=None)

    try:
        request = TtsRequest(**payload)
        result = runtime.synthesize(request)
        _update_task(task_id, status="completed", result=result, error=None)
    except Exception as exc:
        _update_task(task_id, status="failed", error=str(exc))


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "cuda_available": torch.cuda.is_available(),
        "device": DEVICE,
        "model_loaded": runtime.is_loaded(),
        "model_dir": str(MODEL_DIR),
    }


@app.post("/v1/tts", response_model=TtsResponse)
def synthesize(request: TtsRequest) -> dict:
    try:
        return runtime.synthesize(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/v1/tasks/tts", response_model=TaskCreatedResponse, status_code=202)
def create_tts_task(request: TtsRequest, background_tasks: BackgroundTasks) -> dict:
    task_id = str(uuid.uuid4())
    now = time.time()

    with _task_lock:
        _task_store[task_id] = TaskRecord(
            status="queued",
            created_at=now,
            updated_at=now,
            error=None,
            result=None,
        )
        _trim_tasks_locked()

    background_tasks.add_task(_run_tts_task, task_id, request.model_dump())

    return {
        "task_id": task_id,
        "status": "queued",
    }


@app.get("/v1/tasks/{task_id}", response_model=TaskStatusResponse)
def get_tts_task(task_id: str) -> dict:
    with _task_lock:
        task = _task_store.get(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "status": task.status,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "error": task.error,
        "result": task.result,
    }
