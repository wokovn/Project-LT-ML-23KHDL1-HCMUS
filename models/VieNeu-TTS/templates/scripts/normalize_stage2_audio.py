#!/usr/bin/env python3
"""Stage-2 dataset normalization: keep valid rows, convert audio to target format."""

from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

AUDIO_COL_CANDIDATES = [
    "audio_file",
    "audio_filepath",
    "audio_path",
    "audio",
    "path",
    "file",
]


def detect_delimiter(text: str) -> str:
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",|;\t")
        return dialect.delimiter
    except csv.Error:
        first_line = sample.splitlines()[0] if sample else ""
        for candidate in ("|", ",", ";", "\t"):
            if candidate in first_line:
                return candidate
        return ","


def detect_audio_column(fieldnames: list[str]) -> str | None:
    lowered = {f.lower(): f for f in fieldnames}
    for key in AUDIO_COL_CANDIDATES:
        if key in lowered:
            return lowered[key]
    return None


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]], str]:
    raw_text = path.read_text(encoding="utf-8-sig")
    if not raw_text.strip():
        raise ValueError(f"CSV is empty: {path}")

    delimiter = detect_delimiter(raw_text)
    reader = csv.DictReader(io.StringIO(raw_text), delimiter=delimiter)
    if reader.fieldnames is None:
        raise ValueError(f"CSV has no header: {path}")

    rows = list(reader)
    return list(reader.fieldnames), rows, delimiter


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]], delimiter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def normalize_one_file(src: Path, dst: Path, target_sr: int, target_channels: int) -> tuple[bool, bool]:
    audio, sr = sf.read(str(src), always_2d=True)

    sr_changed = int(sr) != target_sr
    ch_changed = int(audio.shape[1]) != target_channels

    if target_channels == 1:
        audio_out = audio.mean(axis=1)
    elif int(audio.shape[1]) == target_channels:
        audio_out = audio
    else:
        raise ValueError(
            f"Unsupported channel conversion: input={audio.shape[1]}, target={target_channels}"
        )

    if int(sr) != target_sr:
        if target_channels == 1:
            audio_out = resample_poly(audio_out, up=target_sr, down=int(sr))
        else:
            resampled = []
            for ch_idx in range(audio_out.shape[1]):
                resampled.append(resample_poly(audio_out[:, ch_idx], up=target_sr, down=int(sr)))
            audio_out = np.stack(resampled, axis=1)

    dst.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dst), np.asarray(audio_out, dtype=np.float32), target_sr)
    return sr_changed, ch_changed


def process_csv(
    csv_path: Path,
    data_root: Path,
    output_root: Path,
    target_sr: int,
    target_channels: int,
) -> None:
    fieldnames, rows, delimiter = read_rows(csv_path)
    audio_col = detect_audio_column(fieldnames)
    if audio_col is None:
        raise ValueError(f"Could not find audio column in {csv_path}: {fieldnames}")

    kept_rows: list[dict[str, str]] = []
    dropped_missing = 0
    dropped_invalid = 0
    sr_converted = 0
    ch_converted = 0

    for row in rows:
        audio_value = (row.get(audio_col) or "").strip()
        if not audio_value:
            dropped_missing += 1
            continue

        src_path = Path(audio_value)
        if not src_path.is_absolute():
            src_path = data_root / src_path

        if not src_path.exists():
            dropped_missing += 1
            continue

        rel_path = Path(audio_value)
        if rel_path.is_absolute():
            try:
                rel_path = src_path.relative_to(data_root)
            except ValueError:
                rel_path = Path(src_path.name)

        dst_path = output_root / rel_path

        try:
            sr_changed, ch_changed = normalize_one_file(
                src=src_path,
                dst=dst_path,
                target_sr=target_sr,
                target_channels=target_channels,
            )
        except Exception:
            dropped_invalid += 1
            continue

        sr_converted += int(sr_changed)
        ch_converted += int(ch_changed)

        row_out = dict(row)
        row_out[audio_col] = rel_path.as_posix()
        kept_rows.append(row_out)

    out_csv = output_root / csv_path.name
    write_rows(out_csv, fieldnames, kept_rows, delimiter)

    print("=" * 72)
    print(f"CSV input:  {csv_path}")
    print(f"CSV output: {out_csv}")
    print(f"rows_total={len(rows)}")
    print(f"rows_kept={len(kept_rows)}")
    print(f"dropped_missing={dropped_missing}")
    print(f"dropped_invalid={dropped_invalid}")
    print(f"sr_converted={sr_converted}")
    print(f"ch_converted={ch_converted}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize stage-2 dataset audio")
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--csv", dest="csv_files", action="append", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--target-sr", type=int, default=24000)
    parser.add_argument("--target-channels", type=int, default=1)
    args = parser.parse_args()

    data_root = args.data_root.resolve()
    output_root = args.output_root.resolve()

    output_root.mkdir(parents=True, exist_ok=True)

    for csv_path in args.csv_files:
        process_csv(
            csv_path=csv_path.resolve(),
            data_root=data_root,
            output_root=output_root,
            target_sr=args.target_sr,
            target_channels=args.target_channels,
        )

    print("\nStage-2 normalization completed.")


if __name__ == "__main__":
    main()
