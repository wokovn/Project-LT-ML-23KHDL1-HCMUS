"""
Audio segmentation and processing module.
"""

import re
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import librosa
import soundfile as sf
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import Config


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
