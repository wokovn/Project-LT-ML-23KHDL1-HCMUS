"""
Audio transcription module using faster-whisper.
"""

import gc
import logging
import sys
import traceback
from pathlib import Path
from typing import Dict, List

import librosa
import torch
from faster_whisper import WhisperModel
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import Config


class Transcriber:
    """Transcribe audio using faster-whisper (CTranslate2).

    Uses int8_float16 quantization for maximum speed on RTX 40xx cards.
    Word-level timestamps enabled for smart slicing.
    All segments default to SPEAKER_00 (no diarization).
    """

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.model = None

    def load_model(self):
        """Load the faster-whisper model onto CUDA with int8_float16."""
        try:
            self._clear_memory()
            self.logger.info(
                f"Loading faster-whisper model: {self.config.whisper_model} "
                f"on {self.config.device} ({self.config.compute_type})"
            )
            self.model = WhisperModel(
                self.config.whisper_model,
                device=self.config.device,
                compute_type=self.config.compute_type
            )
            self._clear_memory()
            self.logger.info("faster-whisper model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load faster-whisper model: {e}")
            self.logger.error(traceback.format_exc())
            raise

    def _clear_memory(self):
        """Run garbage collection and clear CUDA cache if applicable."""
        if self.config.enable_gc:
            gc.collect()
        if self.config.device == "cuda" and self.config.clear_cuda_cache:
            torch.cuda.empty_cache()

    def process(self, audio_path: Path) -> List[Dict]:
        """Transcribe an audio file with word-level timestamps.

        Args:
            audio_path: Path to the WAV audio file.

        Returns:
            List of segment dicts with keys: start, end, text, speaker, words.
        """
        try:
            # Get audio duration for logging
            audio_str = str(audio_path)
            input_duration = librosa.get_duration(filename=audio_str)
            self.logger.info(f"Processing {audio_path.name} ({input_duration:.0f}s)")
            self._clear_memory()

            # Transcribe with faster-whisper (returns a generator)
            seg_generator, info = self.model.transcribe(
                audio_str,
                language=self.config.language,
                beam_size=1,
                temperature=0,
                condition_on_previous_text=False,
                word_timestamps=True,
                vad_filter=True
            )

            self.logger.info(
                f"Detected language: {info.language} (prob={info.language_probability:.2f}), "
                f"duration={info.duration:.0f}s"
            )

            # Consume the generator and build segment list
            segments = []
            for seg in tqdm(
                seg_generator,
                desc=f"  Transcribing ({input_duration:.0f}s audio)",
                unit="seg",
                leave=False
            ):
                segment = {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                    "speaker": "SPEAKER_00",
                    "words": []
                }

                # Extract word-level timestamps for smart slicing
                if seg.words:
                    for word in seg.words:
                        segment["words"].append({
                            "word": word.word.strip(),
                            "start": word.start,
                            "end": word.end
                        })

                segments.append(segment)

            self._clear_memory()

            total_seg_duration = sum(
                s.get('end', 0) - s.get('start', 0) for s in segments
            )
            self.logger.info(
                f"Transcription complete: {len(segments)} segments, "
                f"{total_seg_duration:.0f}s of {input_duration:.0f}s"
            )
            return segments

        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            self.logger.error(traceback.format_exc())
            self._clear_memory()
            return []
