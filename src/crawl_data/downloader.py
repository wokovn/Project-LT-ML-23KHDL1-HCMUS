"""
YouTube audio downloader module.
"""

import re
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import yt_dlp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import Config


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
