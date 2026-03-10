"""
Pipeline orchestration module — ties all components together.
"""

import csv
import re
import logging
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import Config, setup_logging
from downloader import YouTubeDownloader
from transcriber import Transcriber
from audio_processor import AudioProcessor
from text_normalizer import VietnameseTextNormalizer


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
        """Save metadata to comma-separated CSV: audio_file,text,speaker."""
        if not self.metadata_rows:
            self.logger.warning("No metadata to save")
            return

        output_path = self.config.output_dir / "metadata.csv"

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
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
