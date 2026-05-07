"""
xttsv2_prep.py

Script to extract timing/text pairs from JSON transcript files and produce XTTSv2-style metadata
and optional cut audio with ffmpeg.

JSON transcript format (one file per audio):
  [
    {"start": 0.12, "duration": 5.4,   "text": "Trong lúc mà cụ đang ngồi ăn cơm với vợ"},
    {"start": 2.36, "duration": 5.559, "text": "và con thì bị hai người thiếu tướng của"},
    ...
  ]

Directory layout expected:
  transcripts/
    _8QDxBlHZAs.json
    anotherFile.json
    ...
  raw_audio/
    _8QDxBlHZAs.wav
    anotherFile.wav
    ...

Usage examples:
  # dry run: generate metadata only, no audio cutting
  python3 xttsv2_prep.py --transcripts-dir transcripts --audio-dir raw_audio --outdir output --dry-run

  # actually cut audio (requires ffmpeg installed) — this is the DEFAULT behaviour
  python3 xttsv2_prep.py --transcripts-dir transcripts --audio-dir raw_audio --outdir output --sample-rate 22050

  # specify speaker name explicitly
  python3 xttsv2_prep.py --transcripts-dir transcripts --audio-dir raw_audio --outdir output --speaker @QuangDien

Outputs:
  - output/all_raw_metadata.tsv  (columns: source_audio\\tstart\\tend\\ttext\\tspeaker\\tsrc_json)
  - output/full_metadata.csv     (audio_path|text|@speaker)
  - when --cut-audio: wav files saved to output/wavs/
  - split files metadata_train.csv and metadata_eval.csv in output/
"""

from __future__ import annotations
import argparse
import json
import os
import re
import random
import logging
import subprocess
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def strip_diacritics(s: str) -> str:
    """Normalize and remove diacritics; strip non-word chars (used for @SpeakerName)."""
    nk = unicodedata.normalize('NFKD', s)
    only_ascii = ''.join(c for c in nk if not unicodedata.combining(c))
    cleaned = re.sub(r'[^A-Za-z0-9]', '', only_ascii)
    return cleaned


def safe_filename(s: str) -> str:
    """Create a safe ASCII filename (no spaces, limited chars)."""
    nk = unicodedata.normalize('NFKD', s)
    only_ascii = ''.join(c for c in nk if not unicodedata.combining(c))
    out = re.sub(r'[^A-Za-z0-9_.-]', '_', only_ascii)
    return out


# ---------------------------------------------------------------------------
# JSON transcript parsing
# ---------------------------------------------------------------------------

def parse_transcript(json_path: Path) -> List[Dict]:
    """
    Parse a JSON transcript file.

    Each entry is expected to have:
      - "start"    : float  (start time in seconds)
      - "duration" : float  (duration in seconds)
      - "text"     : str    (transcribed sentence)

    Returns a list of dicts with keys: start, end, text.
    """
    try:
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Failed to parse JSON {json_path}: {e}")
        return []

    if not isinstance(data, list):
        logging.error(f"Expected a JSON array in {json_path}, got {type(data).__name__}")
        return []

    records = []
    for i, entry in enumerate(data):
        try:
            start    = float(entry['start'])
            duration = float(entry['duration'])
            text     = str(entry.get('text', '')).strip()
            text     = ' '.join(text.split())   # collapse whitespace
            end      = round(start + duration, 6)
        except (KeyError, TypeError, ValueError) as e:
            logging.warning(f"Skipping malformed entry #{i} in {json_path}: {e}")
            continue

        records.append({'start': start, 'end': end, 'text': text})

    logging.info(f"Parsed {len(records)} segments from {json_path.name}")
    return records


def fix_overlapping_segments(segments: List[Dict]) -> List[Dict]:
    """
    Fix Whisper-style overlapping segments by TRIMMING, not merging.

    Whisper sliding window often produces segments where the next segment
    starts before the current one ends. Merging causes chain reactions
    that produce very long (minutes-long) segments.

    Instead, we trim the end of each segment to the start of the next:
      [0.28 -> 6.32] "Nhin co ve..." + [3.48 -> 8.32] "that la mot..."
      =>
      [0.28 -> 3.48] "Nhin co ve..."   (end trimmed to next start)
      [3.48 -> 8.32] "that la mot..."  (unchanged)

    All original text and segment count are preserved.
    """
    if not segments:
        return []

    sorted_segs = [dict(s) for s in sorted(segments, key=lambda s: s['start'])]
    overlap_count = 0

    for i in range(len(sorted_segs) - 1):
        cur = sorted_segs[i]
        nxt = sorted_segs[i + 1]
        if nxt['start'] < cur['end']:
            overlap_count += 1
            sorted_segs[i]['end'] = nxt['start']  # trim only, never merge

    if overlap_count:
        logging.info(f"Trimmed {overlap_count} overlapping segment(s)")

    # Drop segments that became too short after trimming
    result = [s for s in sorted_segs if s['end'] - s['start'] > 0.05]
    logging.info(f"Overlap fix: {len(segments)} -> {len(result)} segments")
    return result


# ---------------------------------------------------------------------------
# Audio cutting
# ---------------------------------------------------------------------------

def cut_audio_with_ffmpeg(
    src: Path,
    start: float,
    end: float,
    dest: Path,
    ffmpeg_path: str,
    sample_rate: int,
) -> bool:
    """Cut a segment [start, end] from src WAV and write to dest as PCM 16-bit WAV."""
    duration = max(0.0, end - start)
    cmd = [
        ffmpeg_path,
        '-y',                           # overwrite output
        '-i', str(src),
        '-ss', f"{start:.6f}",
        '-t',  f"{duration:.6f}",
        '-acodec', 'pcm_s16le',
        '-ar', str(sample_rate),
        '-ac', '1',                     # mono (XTTSv2 expects mono)
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"ffmpeg failed for {src} -> {dest}: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description='Prepare XTTSv2 training data from JSON transcripts + WAV audio files.'
    )
    p.add_argument('--transcripts-dir', default='data/processed_transcripts',
                   help='Directory containing .json transcript files')
    p.add_argument('--audio-dir', default='data/raw_audio',
                   help='Directory containing .wav audio files (same stem as json)')
    p.add_argument('--outdir', default='data/data_prepared',
                   help='Output directory')
    p.add_argument('--speaker', default='@HUE',
                   help='Speaker name (e.g. @QuangDien). Defaults to @Unknown if omitted.')
    p.add_argument('--no-cut-audio', action='store_true',
                   help='Skip audio cutting (metadata only, same as --dry-run)')
    p.add_argument('--ffmpeg', default='ffmpeg',
                   help='Path to ffmpeg binary')
    p.add_argument('--sample-rate', type=int, default=22050,
                   help='Target sample rate for output wav files (default: 22050)')
    p.add_argument('--dry-run', action='store_true',
                   help='Skip audio cutting; only produce metadata files')
    p.add_argument('--min-duration', type=float, default=0.5,
                   help='Skip segments shorter than this many seconds (default: 0.5)')
    p.add_argument('--min-text-len', type=int, default=3,
                   help='Skip segments with fewer characters than this (default: 3)')
    p.add_argument('--seed', type=int, default=1234,
                   help='Random seed for train/eval split')
    p.add_argument('--eval-frac', type=float, default=0.05,
                   help='Fraction of data reserved for eval set (default: 0.05)')
    args = p.parse_args()

    # ------------------------------------------------------------------
    # Prepare directories
    # ------------------------------------------------------------------
    outdir      = Path(args.outdir)
    wavs_dir    = outdir / 'wavs'
    outdir.mkdir(parents=True, exist_ok=True)
    do_cut = not args.dry_run and not args.no_cut_audio
    if do_cut:
        wavs_dir.mkdir(parents=True, exist_ok=True)

    transcripts_dir = Path(args.transcripts_dir)
    audio_dir       = Path(args.audio_dir)

    # ------------------------------------------------------------------
    # Speaker name
    # ------------------------------------------------------------------
    speaker = args.speaker or '@Unknown'
    if not args.speaker:
        logging.warning("--speaker not provided; using @Unknown")

    # ------------------------------------------------------------------
    # Gather JSON files
    # ------------------------------------------------------------------
    json_files = sorted(transcripts_dir.glob('*.json'))
    if not json_files:
        logging.error(f"No .json files found in {transcripts_dir}")
        return
    logging.info(f"Found {len(json_files)} transcript file(s)")

    # ------------------------------------------------------------------
    # Process each transcript + matching audio
    # ------------------------------------------------------------------
    all_records: List[Dict] = []

    for json_path in json_files:
        stem = json_path.stem   # e.g. "_8QDxBlHZAs"

        # Find matching audio file (prefer .wav, fall back to .mp3 / .flac)
        audio_path: Optional[Path] = None
        for ext in ('.wav', '.mp3', '.flac', '.ogg', '.m4a'):
            candidate = audio_dir / (stem + ext)
            if candidate.exists():
                audio_path = candidate
                break

        if audio_path is None:
            logging.warning(f"No audio file found for transcript {json_path.name}; skipping")
            continue

        segments = parse_transcript(json_path)
        segments = fix_overlapping_segments(segments)

        for idx, seg in enumerate(segments, start=1):
            duration = seg['end'] - seg['start']

            # Filter out very short or empty segments
            if duration < args.min_duration:
                logging.debug(f"Skipping short segment ({duration:.2f}s) in {stem}")
                continue
            if len(seg['text']) < args.min_text_len:
                logging.debug(f"Skipping near-empty text in {stem} segment {idx}")
                continue

            all_records.append({
                'stem':        stem,
                'audio_path':  audio_path,
                'index':       idx,
                'start':       seg['start'],
                'end':         seg['end'],
                'text':        seg['text'],
                'src_json':    str(json_path),
            })

    logging.info(f"Total valid segments: {len(all_records)}")

    if not all_records:
        logging.error("No valid segments found. Check your input files and filter thresholds.")
        return

    # ------------------------------------------------------------------
    # Write all_raw_metadata.tsv
    # ------------------------------------------------------------------
    raw_path = outdir / 'all_raw_metadata.tsv'
    with raw_path.open('w', encoding='utf-8') as f:
        f.write('#source_audio\tstart\tend\ttext\tspeaker\tsrc_json\n')
        for r in all_records:
            text_safe = r['text'].replace('\t', ' ').replace('\n', ' ')
            f.write(
                f"{r['audio_path']}\t{r['start']}\t{r['end']}\t"
                f"{text_safe}\t{speaker}\t{r['src_json']}\n"
            )
    logging.info(f"Wrote raw metadata -> {raw_path}")

    # ------------------------------------------------------------------
    # Build full_metadata.csv (and optionally cut audio)
    # ------------------------------------------------------------------
    full_meta_lines: List[Tuple[str, str, str]] = []

    for r in all_records:
        safe_stem = safe_filename(r['stem'])
        wav_name  = f"{safe_stem}_{r['index']:04d}.wav"
        wav_dest  = wavs_dir / wav_name

        if do_cut:
            success = cut_audio_with_ffmpeg(
                src=r['audio_path'],
                start=r['start'],
                end=r['end'],
                dest=wav_dest,
                ffmpeg_path=args.ffmpeg,
                sample_rate=args.sample_rate,
            )
            if not success:
                logging.error(f"Skipping failed segment: {wav_name}")
                continue
            wav_entry = str(wav_dest)
        else:
            # placeholder path (relative) for dry-run / no-cut-audio mode
            wav_entry = str(Path('wavs') / wav_name)

        # Escape pipe character in text
        text = r['text'].replace('|', ' ')
        full_meta_lines.append((wav_entry, text, speaker))

    full_meta_path = outdir / 'full_metadata.csv'
    with full_meta_path.open('w', encoding='utf-8') as f:
        for wav, text, sp in full_meta_lines:
            f.write(f"{wav}|{text}|{sp}\n")
    logging.info(f"Wrote full metadata -> {full_meta_path}  ({len(full_meta_lines)} lines)")

    # ------------------------------------------------------------------
    # Train / eval split (grouped by source audio stem)
    # ------------------------------------------------------------------
    random.seed(args.seed)

    groups: Dict[str, List] = {}
    for i, (wav, text, sp) in enumerate(full_meta_lines):
        prefix = Path(wav).stem.rsplit('_', 1)[0]   # strip _NNNN index suffix
        groups.setdefault(prefix, []).append((wav, text, sp))

    train:    List[Tuple] = []
    eval_set: List[Tuple] = []

    for prefix, items in groups.items():
        n_eval = max(1, int(round(len(items) * args.eval_frac)))
        if n_eval >= len(items):
            n_eval = max(1, len(items) // 10)
        eval_idxs = set(random.sample(range(len(items)), n_eval))
        for idx, item in enumerate(items):
            (eval_set if idx in eval_idxs else train).append(item)

    logging.info(f"Split: train={len(train)}, eval={len(eval_set)}")

    train_path = outdir / 'metadata_train.csv'
    eval_path  = outdir / 'metadata_eval.csv'

    with train_path.open('w', encoding='utf-8') as f:
        for wav, text, sp in train:
            f.write(f"{wav}|{text}|{sp}\n")

    with eval_path.open('w', encoding='utf-8') as f:
        for wav, text, sp in eval_set:
            f.write(f"{wav}|{text}|{sp}\n")

    logging.info(f"Wrote {train_path.name} and {eval_path.name}")
    logging.info("Done. Check output folder for CSVs and (optionally) wavs.")


if __name__ == '__main__':
    main()