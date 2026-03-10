"""
Pipeline configuration and logging setup.
"""

import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import torch

warnings.filterwarnings('ignore')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass
class Config:
    """Pipeline configuration with sane defaults for Vietnamese TTS."""

    # Paths (project root → data/)
    output_dir: Path = field(default_factory=lambda: DATA_DIR)
    wavs_dir: Path = field(default_factory=lambda: DATA_DIR / "wavs")
    logs_dir: Path = field(default_factory=lambda: DATA_DIR / "logs")
    temp_dir: Path = field(default_factory=lambda: DATA_DIR / "temp")

    # Audio settings
    sample_rate: int = 22050
    audio_format: str = "wav"
    bit_depth: str = "PCM_16"

    # Segment duration window
    min_segment_duration: float = 1.0
    max_segment_duration: float = 8.0

    # Sub-segmentation thresholds
    enable_subsegmentation: bool = True
    subseg_min_length_soft: float = 3.0    # prefer splits >= 3s
    subseg_max_length_hard: float = 7.0    # force split at 7s
    subseg_silence_threshold: float = 0.12 # 120ms gap = natural pause

    # Silence trimming
    trim_top_db: int = 30

    # Whisper ASR
    whisper_model: str = "large-v2"
    compute_type: str = "int8_float16"
    language: str = "vi"

    # Hardware
    device: str = "cuda"

    # VRAM management
    enable_gc: bool = True
    clear_cuda_cache: bool = True

    def __post_init__(self):
        """Create output directories and validate CUDA setup."""
        self.wavs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        if self.device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"GPU: {gpu_name} ({vram_gb:.1f} GB)")
        else:
            print("No CUDA GPU detected — running on CPU.")


def setup_logging(config: Config) -> logging.Logger:
    """Configure dual logging: full detail to file, warnings-only to console."""
    log_file = config.logs_dir / "pipeline.log"

    logger = logging.getLogger("tts_pipeline")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # File handler — captures everything (DEBUG+)
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)

    # Console handler — only warnings and errors (quiet mode)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(ch)

    return logger
