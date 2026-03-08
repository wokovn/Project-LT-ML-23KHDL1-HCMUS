"""
Vietnamese TTS Dataset Pipeline from YouTube
=============================================

End-to-end pipeline to create a Vietnamese TTS dataset from YouTube videos
featuring Central Vietnamese accent content.

Pipeline:
    1. Download audio from YouTube URLs
    2. Transcribe with faster-whisper
    3. Smart-slice segments into 3–7s window
    4. Normalize Vietnamese text
    5. Generate pipe-separated metadata CSV (audio_file|text|speaker)
"""

import sys
import re
import csv
import gc
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import warnings

from tqdm import tqdm
import librosa
import soundfile as sf
import yt_dlp

import torch
from faster_whisper import WhisperModel
from num2words import num2words

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


class YouTubeDownloader:
    """Download audio from YouTube videos using yt-dlp."""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def download(self, url: str) -> Optional[Tuple[Path, Dict]]:
        """Download audio from a YouTube URL.

        Returns:
            Tuple of (audio_path, metadata_dict) or None on failure.
        """
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                self.logger.error(f"Could not extract video ID from: {url}")
                return None

            output_path = self.config.temp_dir / f"{video_id}.wav"

            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }],
                'outtmpl': str(self.config.temp_dir / f"{video_id}"),
                'quiet': True,
                'no_warnings': True,
                'verbose': False,
                'sleep_interval': 3,
                'max_sleep_interval': 15,
                'retries': 20,
                'fragment_retries': 20,
                'extractor_retries': 10,
                'file_access_retries': 10,
                'socket_timeout': 60,
                'http_chunk_size': 10485760,
                'noplaylist': True,
                'no_overwrites': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'skip': ['hls', 'dash'],
                    }
                },
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.youtube.com/',
                'headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                metadata = {
                    'video_id': video_id,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown')
                }

            self.logger.info(f"Downloaded: {metadata['title']} ({video_id})")
            return output_path, metadata

        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return None

    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        """Extract the 11-character video ID from a YouTube URL."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


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
            import traceback
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
            import traceback
            self.logger.error(traceback.format_exc())
            self._clear_memory()
            return []


class AudioProcessor:
    """Slice and normalize audio segments using Smart Slicing.

    Smart Slicing strategy:
        - Segments within [3s, 13s] → saved directly
        - Segments > 13s WITH word timestamps → split at natural pauses
        - Segments > 13s WITHOUT word timestamps → split by silence detection
        - Segments < 3s → discarded (too short for VIVOS-style TTS)

    Goal: Total output duration ≈ total input duration (minimal data loss).
    """

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def _split_segment_by_words(self, segment: Dict) -> List[Dict]:
        """Split a long segment into sub-segments using word-level timestamps.

        Algorithm:
            1. Accumulate words until reaching soft threshold (4s)
            2. Look for natural pause points (silence gaps >= 120ms)
            3. Force split at hard threshold (10s) if no pause found
            4. Ensure splits only occur at word boundaries

        Args:
            segment: A segment dict with 'words' list.

        Returns:
            List of sub-segment dicts, each with start, end, text.
        """
        words = segment.get('words', [])
        if not words:
            return [segment]

        segment_duration = segment.get('end', 0) - segment.get('start', 0)
        if segment_duration <= self.config.max_segment_duration:
            return [segment]

        subsegments = []
        current_words = []
        current_start = segment.get('start', 0)

        for i, word in enumerate(words):
            if 'start' not in word or 'end' not in word:
                continue

            current_words.append(word)
            current_duration = word['end'] - current_start

            should_split = False

            # Hard limit: force split
            if current_duration >= self.config.subseg_max_length_hard:
                should_split = True
            # Soft limit: prefer natural pauses
            elif current_duration >= self.config.subseg_min_length_soft:
                if i + 1 < len(words):
                    next_word = words[i + 1]
                    if 'start' in next_word:
                        gap = next_word['start'] - word['end']
                        if gap >= self.config.subseg_silence_threshold:
                            should_split = True
                elif i == len(words) - 1:
                    should_split = True

            if should_split and current_words:
                text = ' '.join(w.get('word', '') for w in current_words).strip()
                subsegments.append({
                    'start': current_start,
                    'end': word['end'],
                    'text': text,
                    'words': current_words.copy(),
                    'speaker': segment.get('speaker', 'SPEAKER_00')
                })
                current_words = []
                if i + 1 < len(words) and 'start' in words[i + 1]:
                    current_start = words[i + 1]['start']

        # Remaining words
        if current_words:
            text = ' '.join(w.get('word', '') for w in current_words).strip()
            last_word = current_words[-1]
            subsegments.append({
                'start': current_start,
                'end': last_word.get('end', segment.get('end', 0)),
                'text': text,
                'words': current_words,
                'speaker': segment.get('speaker', 'SPEAKER_00')
            })

        if len(subsegments) > 1:
            avg_dur = sum(s['end'] - s['start'] for s in subsegments) / len(subsegments)
            self.logger.debug(
                f"Word-split: {segment_duration:.1f}s → "
                f"{len(subsegments)} sub-segs (avg {avg_dur:.1f}s)"
            )

        return subsegments if subsegments else [segment]

    def _split_by_silence(
        self, audio_path: Path, start: float, end: float, text: str, speaker: str
    ) -> List[Dict]:
        """Fallback splitting by silence detection when word timestamps are unavailable.

        Uses librosa.effects.split() to find non-silent intervals, then groups
        them into chunks within the configured duration window.

        Args:
            audio_path: Source audio file path.
            start: Segment start time (seconds).
            end: Segment end time (seconds).
            text: Transcription text.
            speaker: Speaker ID.

        Returns:
            List of sub-segment dicts.
        """
        duration = end - start
        if duration <= self.config.max_segment_duration:
            return [{'start': start, 'end': end, 'text': text, 'speaker': speaker}]

        try:
            y, sr = librosa.load(
                str(audio_path),
                sr=self.config.sample_rate,
                offset=start,
                duration=duration,
                mono=True
            )
        except Exception as e:
            self.logger.warning(f"Silence-split load failed ({e}), keeping original")
            return [{'start': start, 'end': end, 'text': text, 'speaker': speaker}]

        intervals = librosa.effects.split(y, top_db=self.config.trim_top_db)
        if len(intervals) == 0:
            return [{'start': start, 'end': end, 'text': text, 'speaker': speaker}]

        time_intervals = [(s / sr, e / sr) for s, e in intervals]

        # Group intervals into chunks fitting within max_segment_duration
        subsegments = []
        chunk_start = time_intervals[0][0]
        chunk_end = time_intervals[0][1]

        for i in range(1, len(time_intervals)):
            interval_start, interval_end = time_intervals[i]
            proposed_duration = interval_end - chunk_start

            if proposed_duration > self.config.max_segment_duration:
                abs_start = start + chunk_start
                abs_end = start + chunk_end
                if (abs_end - abs_start) >= self.config.min_segment_duration:
                    subsegments.append({
                        'start': abs_start,
                        'end': abs_end,
                        'text': text if len(subsegments) == 0 else "",
                        'speaker': speaker
                    })
                chunk_start = interval_start
                chunk_end = interval_end
            else:
                chunk_end = interval_end

        # Final chunk
        abs_start = start + chunk_start
        abs_end = start + chunk_end
        if (abs_end - abs_start) >= self.config.min_segment_duration:
            subsegments.append({
                'start': abs_start,
                'end': abs_end,
                'text': text if len(subsegments) == 0 else "",
                'speaker': speaker
            })

        if len(subsegments) > 1:
            avg_dur = sum(s['end'] - s['start'] for s in subsegments) / len(subsegments)
            self.logger.debug(
                f"Silence-split: {duration:.1f}s → "
                f"{len(subsegments)} sub-segs (avg {avg_dur:.1f}s)"
            )

        return subsegments if subsegments else [
            {'start': start, 'end': end, 'text': text, 'speaker': speaker}
        ]

    def process_segments(
        self,
        audio_path: Path,
        segments: List[Dict],
        video_id: str
    ) -> List[Dict]:
        """Extract, smart-slice, and save audio segments as WAV files.

        All duration-based splitting happens here. Segments arrive unfiltered;
        long segments are recursively split, short fragments are discarded.

        Args:
            audio_path: Source audio file.
            segments: Transcription segments from Transcriber.
            video_id: YouTube video identifier (for filenames).

        Returns:
            List of metadata dicts for successfully saved segments.
        """
        processed = []
        seg_counter = 0

        total_input_duration = sum(
            s.get('end', 0) - s.get('start', 0) for s in segments
        )

        for seg in tqdm(segments, desc="Slicing audio", leave=False):
            try:
                duration = seg.get("end", 0) - seg.get("start", 0)

                if duration > self.config.max_segment_duration:
                    # Smart Slicing: word-level split first, silence-based fallback
                    has_words = 'words' in seg and seg['words']
                    if has_words and self.config.enable_subsegmentation:
                        subsegments = self._split_segment_by_words(seg)
                    else:
                        subsegments = self._split_by_silence(
                            audio_path,
                            seg.get('start', 0),
                            seg.get('end', 0),
                            seg.get('text', ''),
                            seg.get('speaker', 'SPEAKER_00')
                        )

                    # Recursive fallback for still-too-long sub-segments
                    final_subsegments = []
                    for subseg in subsegments:
                        sub_dur = subseg.get('end', 0) - subseg.get('start', 0)
                        if sub_dur > self.config.max_segment_duration:
                            deeper = self._split_by_silence(
                                audio_path,
                                subseg.get('start', 0),
                                subseg.get('end', 0),
                                subseg.get('text', ''),
                                subseg.get('speaker', 'SPEAKER_00')
                            )
                            final_subsegments.extend(deeper)
                        else:
                            final_subsegments.append(subseg)

                    for subseg in final_subsegments:
                        sub_dur = subseg.get('end', 0) - subseg.get('start', 0)
                        if sub_dur < self.config.min_segment_duration:
                            continue
                        if sub_dur > self.config.max_segment_duration:
                            # Unsplittable chunk — discard to keep TTS data clean
                            self.logger.debug(
                                f"Discarding unsplittable {sub_dur:.1f}s chunk "
                                f"(>{self.config.max_segment_duration}s limit)"
                            )
                            continue
                        filename = f"{video_id}_{seg_counter:04d}.wav"
                        seg_counter += 1
                        metadata = self._extract_and_save_segment(
                            audio_path, subseg, filename
                        )
                        if metadata:
                            processed.append(metadata)

                elif duration >= self.config.min_segment_duration:
                    filename = f"{video_id}_{seg_counter:04d}.wav"
                    seg_counter += 1
                    metadata = self._extract_and_save_segment(
                        audio_path, seg, filename
                    )
                    if metadata:
                        processed.append(metadata)

                # Segments < min_segment_duration (1s) are silently ignored

            except Exception as e:
                self.logger.warning(f"Segment processing error: {e}")
                continue

        # Data-loss reporting (logged to file only)
        total_output_duration = sum(seg.get('duration', 0) for seg in processed)
        loss_pct = (1 - total_output_duration / max(total_input_duration, 0.01)) * 100

        self.logger.info(
            f"Segmentation: {len(processed)} saved, "
            f"{total_input_duration:.0f}s in → {total_output_duration:.0f}s out "
            f"(loss: {loss_pct:.1f}%)"
        )
        if loss_pct > 20:
            self.logger.warning(
                f"Data loss is {loss_pct:.1f}% (> 20%). "
                "Check audio quality or adjust silence thresholds."
            )

        return processed

    def _extract_and_save_segment(
        self,
        audio_path: Path,
        segment: Dict,
        filename: str
    ) -> Optional[Dict]:
        """Extract a single audio segment, trim silence, and save as WAV.

        Args:
            audio_path: Source audio file.
            segment: Segment dict with start, end, text, speaker.
            filename: Output WAV filename.

        Returns:
            Metadata dict with audio_file, text, speaker, duration — or None.
        """
        try:
            output_path = self.config.wavs_dir / filename

            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            duration = end_time - start_time

            if duration < self.config.min_segment_duration:
                return None

            # Hallucination guard: short segments (<2s) with empty/punctuation-only text
            text = segment.get("text", "").strip()
            if duration < 2.0:
                cleaned = re.sub(r'[^\w]', '', text)
                if not cleaned:
                    return None

            y, sr = librosa.load(
                str(audio_path),
                sr=self.config.sample_rate,
                offset=start_time,
                duration=duration,
                mono=True
            )

            y_trimmed, _ = librosa.effects.trim(y, top_db=self.config.trim_top_db)

            if len(y_trimmed) < self.config.sample_rate * 0.5:
                return None

            sf.write(
                str(output_path),
                y_trimmed,
                self.config.sample_rate,
                subtype=self.config.bit_depth
            )

            actual_duration = len(y_trimmed) / self.config.sample_rate
            return {
                'audio_file': f"wavs/{filename}",
                'text': segment.get("text", ""),
                'speaker': segment.get('speaker', 'SPEAKER_00'),
                'duration': actual_duration  # internal use for stats; excluded from CSV
            }

        except Exception as e:
            self.logger.warning(f"Failed to extract {filename}: {e}")
            return None


class VietnameseTextNormalizer:
    """Normalize Vietnamese text for TTS training.

    Handles: lowercasing, emoji removal, number/date/percentage expansion,
    and stripping of non-Vietnamese characters.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.digit_map = {
            '0': 'không', '1': 'một', '2': 'hai', '3': 'ba', '4': 'bốn',
            '5': 'năm', '6': 'sáu', '7': 'bảy', '8': 'tám', '9': 'chín'
        }

    def normalize(self, text: str) -> str:
        """Normalize a Vietnamese text string for TTS.

        Args:
            text: Raw transcription text.

        Returns:
            Cleaned, lowercased text with numbers expanded to words.
        """
        if not text:
            return ""

        text = text.lower()
        text = self._remove_emojis(text)
        text = self._expand_numbers(text)
        text = self._expand_dates(text)
        text = self._expand_percentages(text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(
            r'[^a-záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ\s.,!?]',
            '', text
        )
        return text

    @staticmethod
    def _remove_emojis(text: str) -> str:
        """Strip emoji and symbol characters."""
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text)

    def _expand_numbers(self, text: str) -> str:
        """Expand numeric tokens to Vietnamese words."""
        def replace_number(match):
            num_str = match.group(0)
            try:
                num = int(num_str)
                return num2words(num, lang='vi')
            except Exception:
                return ' '.join(self.digit_map.get(d, d) for d in num_str)

        return re.sub(r'\b\d+\b', replace_number, text)

    def _expand_dates(self, text: str) -> str:
        """Expand date formats (DD/MM or DD/MM/YYYY) to Vietnamese words."""
        def replace_date(match):
            day = match.group(1)
            month = match.group(2)
            year = match.group(3) if match.group(3) else ""
            result = f"ngày {num2words(int(day), lang='vi')} tháng {num2words(int(month), lang='vi')}"
            if year:
                result += f" năm {num2words(int(year), lang='vi')}"
            return result

        return re.sub(r'\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b', replace_date, text)

    def _expand_percentages(self, text: str) -> str:
        """Expand percentage symbols to Vietnamese words."""
        def replace_percent(match):
            num = match.group(1)
            return f"{num2words(int(num), lang='vi')} phần trăm"

        return re.sub(r'(\d+)\s*%', replace_percent, text)


class TTSDatasetPipeline:
    """Orchestrate the full TTS dataset creation pipeline."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(config)

        self.downloader = YouTubeDownloader(config, self.logger)
        self.transcriber = Transcriber(config, self.logger)
        self.audio_processor = AudioProcessor(config, self.logger)
        self.text_normalizer = VietnameseTextNormalizer(self.logger)

        self.metadata_rows = []

    def run(self, youtube_urls: List[str]):
        """Run the complete pipeline over a list of YouTube URLs.

        Args:
            youtube_urls: List of YouTube video URLs to process.
        """
        print(f"\nStarting pipeline — {len(youtube_urls)} video(s)")

        self.transcriber.load_model()

        for i, url in enumerate(youtube_urls, 1):
            print(f"\n▶ [{i}/{len(youtube_urls)}] {url}")
            try:
                self._process_video(url)
            except Exception as e:
                self.logger.error(f"Failed to process {url}: {e}")
                continue

        self._save_metadata()
        self._cleanup_temp()

        # Final summary
        total_duration = sum(r.get('duration', 0) for r in self.metadata_rows)
        print(f"\n{'═' * 50}")
        print(f"Done! Processed {len(youtube_urls)} video(s).")
        print(f"Stats: {len(self.metadata_rows)} segments | Total audio: {total_duration:.0f}s")
        print(f"Output: {self.config.output_dir.absolute() / 'metadata.csv'}")
        print(f"{'═' * 50}\n")

    def _process_video(self, url: str):
        """Process a single YouTube video through the full pipeline.

        Args:
            url: YouTube video URL.
        """
        download_result = self.downloader.download(url)
        if not download_result:
            return
        audio_path, metadata = download_result
        video_id = metadata['video_id']

        segments = self.transcriber.process(audio_path)
        if not segments:
            self.logger.warning(f"No segments extracted from {video_id}")
            return

        processed_segments = self.audio_processor.process_segments(
            audio_path, segments, video_id
        )

        for seg in processed_segments:
            seg['text'] = self.text_normalizer.normalize(seg['text'])

        self.metadata_rows.extend(processed_segments)
        print(f"{video_id}: {len(processed_segments)} segments saved")

    def _save_metadata(self):
        """Save metadata to pipe-separated CSV: audio_file|text|speaker."""
        if not self.metadata_rows:
            self.logger.warning("No metadata to save")
            return

        output_path = self.config.output_dir / "metadata.csv"

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter='|', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['audio_file', 'text', 'speaker'])

            for row in self.metadata_rows:
                # Sanitize text: collapse newlines/whitespace into single line
                text = row.get('text', '')
                text = re.sub(r'[\r\n]+', ' ', text).strip()
                text = re.sub(r'\s+', ' ', text)

                writer.writerow([
                    row.get('audio_file', ''),
                    text,
                    row.get('speaker', 'SPEAKER_00')
                ])

        self.logger.info(f"Saved metadata: {output_path} ({len(self.metadata_rows)} rows)")

        # Full stats to log file only
        self.logger.info(f"  Total samples:  {len(self.metadata_rows)}")
        durations = [r.get('duration', 0) for r in self.metadata_rows]
        if durations:
            total_dur = sum(durations)
            self.logger.info(f"  Total duration: {total_dur:.1f}s ({total_dur/60:.1f} min)")
            self.logger.info(f"  Avg duration:   {total_dur/len(durations):.2f}s")
            self.logger.info(f"  Min duration:   {min(durations):.2f}s")
            self.logger.info(f"  Max duration:   {max(durations):.2f}s")

    def _cleanup_temp(self):
        """Remove temporary download files."""
        try:
            for file in self.config.temp_dir.glob("*"):
                file.unlink()
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")


def main():
    """Entry point: load config, read URLs, and run the pipeline."""
    config = Config()

    print("\n" + "═" * 50)
    print("Vietnamese TTS Dataset Pipeline")
    print("═" * 50)
    print(f"Model:      {config.whisper_model}")
    print(f"Device:     {config.device}")
    print(f"Compute:    {config.compute_type}")
    print(f"Language:   {config.language}")
    print(f"Seg window: [{config.min_segment_duration}s, {config.max_segment_duration}s]")
    print("═" * 50)

    urls_file = PROJECT_ROOT / "src" / "crawl_data" / "youtube_urls.txt"
    if urls_file.exists():
        with open(urls_file, 'r', encoding='utf-8') as f:
            youtube_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        print(f"{urls_file} not found. Create it with one YouTube URL per line.")
        sys.exit(1)

    if not youtube_urls:
        print("No URLs found in youtube_urls.txt")
        sys.exit(1)

    print(f"{len(youtube_urls)} URL(s) queued\n")

    pipeline = TTSDatasetPipeline(config)
    pipeline.run(youtube_urls)


if __name__ == "__main__":
    main()