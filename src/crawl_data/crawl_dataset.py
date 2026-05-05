"""
Vietnamese TTS Dataset Pipeline — Download Audio + YouTube Transcript
=====================================================================

Tải audio WAV và bản chép lời trực tiếp từ YouTube (không dùng Whisper).
Ưu tiên transcript thủ công, fallback sang transcript tự động (vi).

Output:
    data/raw_audio/<video_id>.wav
    data/transcripts/<video_id>.json   ← danh sách {start, duration, text}

Cài đặt:
    pip install yt-dlp youtube-transcript-api
"""

import sys
import re
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass, field

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
try:
    from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled
except ImportError:
    # Phiên bản mới chuyển exception vào submodule _errors
    from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass
class Config:
    output_dir:      Path = field(default_factory=lambda: DATA_DIR / "raw_audio")
    transcript_dir:  Path = field(default_factory=lambda: DATA_DIR / "transcripts")
    logs_dir:        Path = field(default_factory=lambda: DATA_DIR / "logs")

    # Ngôn ngữ ưu tiên khi lấy transcript
    preferred_langs: List[str] = field(default_factory=lambda: ["vi"])

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


def setup_logging(config: Config) -> logging.Logger:
    log_file = config.logs_dir / "download.log"
    logger = logging.getLogger("downloader")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(ch)

    return logger


# ─────────────────────────────────────────────
# Transcript
# ─────────────────────────────────────────────

class TranscriptFetcher:
    """Lấy bản chép lời từ YouTube qua youtube-transcript-api."""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def fetch(self, video_id: str) -> Optional[List[Dict]]:
        """Lấy transcript cho một video.

        Tự động nhận diện phiên bản youtube-transcript-api (cũ < 0.6 hay mới >= 0.6).
        Ưu tiên: transcript thủ công → transcript tự động (tiếng Việt).

        Returns:
            Danh sách dict {start, duration, text} hoặc None nếu không có.
        """
        try:
            # Phiên bản mới (>= 0.6): YouTubeTranscriptApi là instance, dùng .list()
            # Phiên bản cũ (< 0.6): YouTubeTranscriptApi là class, dùng .list_transcripts()
            use_new_api = not hasattr(YouTubeTranscriptApi, "list_transcripts")

            if use_new_api:
                api = YouTubeTranscriptApi()
                transcript_list = api.list(video_id)
            else:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Thử thủ công trước, fallback tự động
            try:
                transcript = transcript_list.find_manually_created_transcript(
                    self.config.preferred_langs
                )
                source = "thủ công"
            except NoTranscriptFound:
                transcript = transcript_list.find_generated_transcript(
                    self.config.preferred_langs
                )
                source = "tự động"

            fetched = transcript.fetch()

            # API mới trả về FetchedTranscript (iterable object), cần convert sang list[dict]
            if isinstance(fetched, list):
                data = fetched
            else:
                data = [
                    {"start": s.start, "duration": s.duration, "text": s.text}
                    for s in fetched
                ]

            self.logger.info(f"[{video_id}] Transcript {source} — {len(data)} đoạn")
            return data

        except TranscriptsDisabled:
            self.logger.warning(f"[{video_id}] Video đã tắt transcript.")
            return None
        except NoTranscriptFound:
            self.logger.warning(f"[{video_id}] Không tìm thấy transcript tiếng Việt.")
            return None
        except Exception as e:
            self.logger.error(f"[{video_id}] Lỗi khi lấy transcript: {e}")
            return None

    def save(self, video_id: str, data: List[Dict]) -> Path:
        """Lưu transcript ra file JSON."""
        out_path = self.config.transcript_dir / f"{video_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return out_path


# ─────────────────────────────────────────────
# Downloader
# ─────────────────────────────────────────────

class YouTubeDownloader:
    """Tải audio từ YouTube và lưu thành file WAV."""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def download(self, url: str) -> Optional[Tuple[Path, Dict]]:
        """Tải audio WAV từ một YouTube URL.

        Returns:
            (đường dẫn WAV, metadata) hoặc None nếu thất bại.
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            self.logger.error(f"Không lấy được video ID từ: {url}")
            return None

        output_path = self.config.output_dir / f"{video_id}.wav"

        if output_path.exists():
            print(f"  ⏭  Audio đã tồn tại, bỏ qua: {video_id}.wav")
            return output_path, {"video_id": video_id, "skipped": True}

        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }],
            "outtmpl": str(self.config.output_dir / video_id),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "no_overwrites": True,
            "sleep_interval": 3,
            "max_sleep_interval": 15,
            "retries": 20,
            "fragment_retries": 20,
            "extractor_retries": 10,
            "file_access_retries": 10,
            "socket_timeout": 60,
            "http_chunk_size": 10485760,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                    "skip": ["hls", "dash"],
                }
            },
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "referer": "https://www.youtube.com/",
            "headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                metadata = {
                    "video_id": video_id,
                    "title":    info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", "Unknown"),
                }
            self.logger.info(f"Đã tải: {metadata['title']} ({video_id})")
            return output_path, metadata

        except Exception as e:
            self.logger.error(f"Thất bại khi tải {url}: {e}")
            return None

    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    config = Config()
    logger = setup_logging(config)

    print("\n" + "═" * 55)
    print("YouTube Audio + Transcript Downloader")
    print("═" * 55)
    print(f"Audio    → {config.output_dir.absolute()}")
    print(f"Transcript → {config.transcript_dir.absolute()}")
    print("═" * 55)

    urls_file = PROJECT_ROOT / "src" / "crawl_data" / "youtube_urls.txt"
    if not urls_file.exists():
        print(f"Không tìm thấy: {urls_file}")
        print("Hãy tạo file với mỗi dòng là một YouTube URL.")
        sys.exit(1)

    with open(urls_file, "r", encoding="utf-8") as f:
        urls = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

    if not urls:
        print("Không có URL nào trong file.")
        sys.exit(1)

    print(f"{len(urls)} URL(s) trong hàng đợi\n")

    downloader = YouTubeDownloader(config, logger)
    fetcher    = TranscriptFetcher(config, logger)

    stats = {"audio_ok": 0, "audio_fail": 0, "transcript_ok": 0, "transcript_fail": 0}

    for i, url in enumerate(urls, 1):
        print(f"▶ [{i}/{len(urls)}] {url}")

        # ── 1. Tải audio ──────────────────────────────
        result = downloader.download(url)
        if result:
            audio_path, meta = result
            video_id = meta["video_id"]
            if not meta.get("skipped"):
                print(f"  ✓  Audio: {audio_path.name}  ({meta.get('duration', 0):.0f}s)")
            stats["audio_ok"] += 1
        else:
            print(f"  ✗  Audio thất bại, bỏ qua transcript.")
            stats["audio_fail"] += 1
            continue

        # ── 2. Lấy transcript ─────────────────────────
        transcript_path = config.transcript_dir / f"{video_id}.json"
        if transcript_path.exists():
            print(f"  ⏭  Transcript đã tồn tại, bỏ qua.")
            stats["transcript_ok"] += 1
            continue

        transcript_data = fetcher.fetch(video_id)
        if transcript_data:
            saved = fetcher.save(video_id, transcript_data)
            print(f"  ✓  Transcript: {saved.name}  ({len(transcript_data)} đoạn)")
            stats["transcript_ok"] += 1
        else:
            print(f"  ✗  Không lấy được transcript cho {video_id}")
            stats["transcript_fail"] += 1

    print(f"\n{'═' * 55}")
    print(f"Hoàn tất!")
    print(f"  Audio    : ✓ {stats['audio_ok']}  ✗ {stats['audio_fail']}")
    print(f"  Transcript: ✓ {stats['transcript_ok']}  ✗ {stats['transcript_fail']}")
    print(f"{'═' * 55}\n")


if __name__ == "__main__":
    main()