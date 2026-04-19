#!/usr/bin/env python3
"""Quick dataset alignment check for model-specific audio/text expectations."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

try:
    import soundfile as sf
except ImportError as exc:  # pragma: no cover
    print("Missing dependency: soundfile. Install with: pip install soundfile")
    raise SystemExit(2) from exc

AUDIO_COL_CANDIDATES = [
    "audio_filepath",
    "audio_path",
    "audio_file",
    "wav_path",
    "wav",
    "path",
    "file",
]
TEXT_COL_CANDIDATES = ["text", "transcript", "sentence", "normalized_text"]


def detect_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    lowered = {name.lower(): name for name in fieldnames}
    for key in candidates:
        if key in lowered:
            return lowered[key]
    return None


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        rows = list(reader)
        return list(reader.fieldnames), rows


def resolve_audio_path(data_root: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return data_root / p


def inspect_csv(
    csv_path: Path,
    data_root: Path,
    expected_sr: int,
    expected_channels: int,
    max_samples: int,
    seed: int,
) -> dict[str, int | float | str]:
    fields, rows = read_csv(csv_path)
    audio_col = detect_column(fields, AUDIO_COL_CANDIDATES)
    text_col = detect_column(fields, TEXT_COL_CANDIDATES)

    if audio_col is None:
        raise ValueError(
            f"Could not detect audio column in {csv_path}. Found headers: {fields}"
        )

    rng = random.Random(seed)
    sampled_rows = rows.copy()
    rng.shuffle(sampled_rows)
    sampled_rows = sampled_rows[: min(max_samples, len(sampled_rows))]

    missing_files = 0
    sr_mismatch = 0
    channel_mismatch = 0
    empty_text = 0
    duration_sum = 0.0
    duration_min = float("inf")
    duration_max = 0.0

    for row in sampled_rows:
        audio_raw = (row.get(audio_col) or "").strip()
        if not audio_raw:
            missing_files += 1
            continue

        audio_path = resolve_audio_path(data_root, audio_raw)
        if not audio_path.exists():
            missing_files += 1
            continue

        info = sf.info(str(audio_path))
        sr = int(info.samplerate)
        channels = int(info.channels)
        duration = float(info.frames) / float(sr) if sr > 0 else 0.0

        duration_sum += duration
        duration_min = min(duration_min, duration)
        duration_max = max(duration_max, duration)

        if sr != expected_sr:
            sr_mismatch += 1
        if channels != expected_channels:
            channel_mismatch += 1

        if text_col is not None:
            text_value = (row.get(text_col) or "").strip()
            if not text_value:
                empty_text += 1

    checked = len(sampled_rows)
    avg_duration = (duration_sum / checked) if checked > 0 else 0.0

    return {
        "csv": str(csv_path),
        "checked": checked,
        "missing_files": missing_files,
        "sr_mismatch": sr_mismatch,
        "channel_mismatch": channel_mismatch,
        "empty_text": empty_text,
        "avg_duration_sec": round(avg_duration, 3),
        "min_duration_sec": 0.0 if duration_min == float("inf") else round(duration_min, 3),
        "max_duration_sec": round(duration_max, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Model-specific dataset smoke check")
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--csv", dest="csv_files", action="append", required=True, type=Path)
    parser.add_argument("--expected-sr", type=int, default=24000)
    parser.add_argument("--expected-channels", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20260419)
    parser.add_argument("--fail-on-warning", action="store_true")
    args = parser.parse_args()

    overall_warnings = 0

    for idx, csv_path in enumerate(args.csv_files):
        stats = inspect_csv(
            csv_path=csv_path,
            data_root=args.data_root,
            expected_sr=args.expected_sr,
            expected_channels=args.expected_channels,
            max_samples=args.max_samples,
            seed=args.seed + idx,
        )

        print("=" * 72)
        print(f"CSV: {stats['csv']}")
        print(f"checked={stats['checked']}")
        print(f"missing_files={stats['missing_files']}")
        print(f"sr_mismatch={stats['sr_mismatch']}")
        print(f"channel_mismatch={stats['channel_mismatch']}")
        print(f"empty_text={stats['empty_text']}")
        print(f"avg_duration_sec={stats['avg_duration_sec']}")
        print(f"min_duration_sec={stats['min_duration_sec']}")
        print(f"max_duration_sec={stats['max_duration_sec']}")

        warnings_here = (
            int(stats["missing_files"]) + int(stats["sr_mismatch"]) + int(stats["channel_mismatch"]) + int(stats["empty_text"])
        )
        overall_warnings += warnings_here

    if args.fail_on_warning and overall_warnings > 0:
        print("\nSmoke check failed because warnings were found.")
        sys.exit(1)

    print("\nSmoke check completed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
