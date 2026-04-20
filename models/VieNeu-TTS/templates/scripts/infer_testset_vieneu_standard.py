#!/usr/bin/env python3
"""Run test-set waveform inference for a VieNeu checkpoint (standard backend)."""

from __future__ import annotations

import argparse
import csv
import traceback
import wave
from collections import defaultdict
from pathlib import Path

import numpy as np


def _detect_delimiter(first_line: str) -> str:
    for candidate in ("|", ",", ";", "\t"):
        if candidate in first_line:
            return candidate
    return ","


def _read_csv_rows(csv_path: Path, delimiter: str | None = None) -> list[dict[str, str]]:
    raw = csv_path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return []

    lines = raw.splitlines()
    delim = delimiter or _detect_delimiter(lines[0])
    reader = csv.DictReader(lines, delimiter=delim)
    rows = []
    for row in reader:
        rows.append({k: (v or "") for k, v in row.items() if k is not None})
    return rows


def _detect_column(fieldnames: list[str], candidates: list[str], override: str | None) -> str:
    if override:
        if override not in fieldnames:
            raise ValueError(f"Column '{override}' not found. Available: {fieldnames}")
        return override

    lowered = {name.lower(): name for name in fieldnames}
    for c in candidates:
        if c in lowered:
            return lowered[c]
    raise ValueError(f"No matching column from {candidates}. Available: {fieldnames}")


def _save_wav_16bit(audio: np.ndarray, wav_path: Path, sample_rate: int) -> None:
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(audio, dtype=np.float32)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=-1.0)
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767.0).astype(np.int16)

    with wave.open(wav_path.as_posix(), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Infer test-set WAVs from a VieNeu checkpoint")
    parser.add_argument("--backbone-repo", required=True, help="Checkpoint/folder path for model weights")
    parser.add_argument("--test-csv", required=True)
    parser.add_argument("--data-root", default="data/xtts_stage2_24k_mono")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest-out", required=True)
    parser.add_argument("--errors-out", default=None)
    parser.add_argument("--delimiter", default=None)
    parser.add_argument("--audio-col", default=None)
    parser.add_argument("--text-col", default=None)
    parser.add_argument("--speaker-col", default=None)
    parser.add_argument("--backbone-device", default="cuda")
    parser.add_argument("--codec-repo", default="neuphonic/distill-neucodec")
    parser.add_argument("--codec-device", default="cuda")
    parser.add_argument("--max-chars", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        from tqdm import tqdm
        from vieneu import Vieneu
    except Exception as exc:
        raise RuntimeError("Missing dependencies for inference (vieneu/tqdm)") from exc

    test_csv = Path(args.test_csv)
    data_root = Path(args.data_root)
    output_dir = Path(args.output_dir)
    manifest_out = Path(args.manifest_out)
    errors_out = Path(args.errors_out) if args.errors_out else manifest_out.with_name(manifest_out.stem + "_errors.csv")

    if not test_csv.exists():
        raise FileNotFoundError(f"test csv not found: {test_csv}")

    rows = _read_csv_rows(test_csv, delimiter=args.delimiter)
    if not rows:
        raise RuntimeError(f"test csv has no rows: {test_csv}")

    fieldnames = list(rows[0].keys())
    audio_col = _detect_column(fieldnames, ["audio_file", "wav", "wav_path", "audio_path", "path", "file"], args.audio_col)
    text_col = _detect_column(fieldnames, ["text", "transcript", "sentence", "normalized_text"], args.text_col)

    speaker_col = None
    if args.speaker_col:
        if args.speaker_col not in fieldnames:
            raise ValueError(f"speaker column '{args.speaker_col}' not in csv headers: {fieldnames}")
        speaker_col = args.speaker_col
    else:
        lowered = {name.lower(): name for name in fieldnames}
        for candidate in ["speaker_name", "speaker", "speaker_id", "spk"]:
            if candidate in lowered:
                speaker_col = lowered[candidate]
                break

    if args.limit > 0:
        rows = rows[: args.limit]

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    errors_out.parent.mkdir(parents=True, exist_ok=True)

    print(f"loading_model={args.backbone_repo}")
    tts = Vieneu(
        mode="standard",
        backbone_repo=args.backbone_repo,
        backbone_device=args.backbone_device,
        codec_repo=args.codec_repo,
        codec_device=args.codec_device,
    )

    manifest_rows = []
    error_rows = []
    num_ok = 0
    num_skip = 0

    work_items = []
    for idx, row in enumerate(rows, start=1):
        audio_rel = (row.get(audio_col, "") or "").strip()
        text_val = (row.get(text_col, "") or "").strip()
        speaker_val = (row.get(speaker_col, "") or "").strip() if speaker_col else "__single__"
        utt_id = Path(audio_rel).stem if audio_rel else f"utt_{idx:06d}"

        if not audio_rel:
            error_rows.append({"utt_id": utt_id, "error": "missing audio path", "trace": ""})
            continue
        if not text_val:
            error_rows.append({"utt_id": utt_id, "error": "missing text", "trace": ""})
            continue

        ref_wav = (data_root / audio_rel).resolve()
        gen_wav = (output_dir / audio_rel).resolve()

        if args.skip_existing and gen_wav.exists():
            num_skip += 1
            manifest_rows.append(
                {
                    "utt_id": utt_id,
                    "reference_wav": ref_wav.as_posix(),
                    "generated_wav": gen_wav.as_posix(),
                    "status": "skipped_existing",
                }
            )
            continue

        if not ref_wav.exists():
            error_rows.append({"utt_id": utt_id, "error": f"missing reference wav: {ref_wav}", "trace": ""})
            continue

        work_items.append(
            {
                "utt_id": utt_id,
                "speaker": speaker_val,
                "text": text_val,
                "reference_wav": ref_wav,
                "generated_wav": gen_wav,
            }
        )

    use_batched = args.batch_size > 1 and speaker_col is not None

    if use_batched:
        speaker_groups = defaultdict(list)
        for item in work_items:
            speaker_groups[item["speaker"]].append(item)

        print(f"batched_mode=true speaker_col={speaker_col} num_speakers={len(speaker_groups)} batch_size={args.batch_size}")

        for speaker, group_items in speaker_groups.items():
            ref_item = group_items[0]
            try:
                ref_codes = tts.encode_reference(ref_item["reference_wav"].as_posix())
                ref_text = ref_item["text"]
            except Exception as exc:
                for item in group_items:
                    error_rows.append(
                        {
                            "utt_id": item["utt_id"],
                            "error": f"encode_reference_failed speaker={speaker}: {exc}",
                            "trace": traceback.format_exc(limit=1).strip(),
                        }
                    )
                continue

            for start in tqdm(range(0, len(group_items), args.batch_size), desc=f"Infer speaker {speaker}", unit="batch"):
                batch = group_items[start : start + args.batch_size]
                texts = [x["text"] for x in batch]

                try:
                    audios = tts.infer_batch(
                        texts,
                        ref_codes=ref_codes,
                        ref_text=ref_text,
                        apply_watermark=True,
                    )

                    if len(audios) != len(batch):
                        raise RuntimeError(f"infer_batch output size mismatch: {len(audios)} vs {len(batch)}")

                    for item, audio in zip(batch, audios):
                        _save_wav_16bit(audio, item["generated_wav"], sample_rate=24_000)
                        manifest_rows.append(
                            {
                                "utt_id": item["utt_id"],
                                "reference_wav": item["reference_wav"].as_posix(),
                                "generated_wav": item["generated_wav"].as_posix(),
                                "status": "ok",
                            }
                        )
                        num_ok += 1
                except Exception:
                    # Fallback to single-item infer to keep progress robust.
                    for item in batch:
                        try:
                            audio = tts.infer(
                                text=item["text"],
                                ref_codes=ref_codes,
                                ref_text=ref_text,
                                max_chars=args.max_chars,
                            )
                            _save_wav_16bit(audio, item["generated_wav"], sample_rate=24_000)
                            manifest_rows.append(
                                {
                                    "utt_id": item["utt_id"],
                                    "reference_wav": item["reference_wav"].as_posix(),
                                    "generated_wav": item["generated_wav"].as_posix(),
                                    "status": "ok",
                                }
                            )
                            num_ok += 1
                        except Exception as exc:
                            error_rows.append(
                                {
                                    "utt_id": item["utt_id"],
                                    "error": str(exc),
                                    "trace": traceback.format_exc(limit=1).strip(),
                                }
                            )
    else:
        for item in tqdm(work_items, desc="Infer test set", unit="utt"):
            try:
                audio = tts.infer(
                    text=item["text"],
                    ref_audio=item["reference_wav"].as_posix(),
                    ref_text=item["text"],
                    max_chars=args.max_chars,
                )
                _save_wav_16bit(audio, item["generated_wav"], sample_rate=24_000)

                manifest_rows.append(
                    {
                        "utt_id": item["utt_id"],
                        "reference_wav": item["reference_wav"].as_posix(),
                        "generated_wav": item["generated_wav"].as_posix(),
                        "status": "ok",
                    }
                )
                num_ok += 1
            except Exception as exc:
                error_rows.append(
                    {
                        "utt_id": item["utt_id"],
                        "error": str(exc),
                        "trace": traceback.format_exc(limit=1).strip(),
                    }
                )

    try:
        tts.close()
    except Exception:
        pass

    with manifest_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["utt_id", "reference_wav", "generated_wav", "status"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    with errors_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["utt_id", "error", "trace"])
        writer.writeheader()
        writer.writerows(error_rows)

    print(f"num_rows={len(rows)}")
    print(f"num_ok={num_ok}")
    print(f"num_skipped_existing={num_skip}")
    print(f"num_error={len(error_rows)}")
    print(f"manifest_out={manifest_out}")
    print(f"errors_out={errors_out}")
    print(f"generated_dir={output_dir}")


if __name__ == "__main__":
    main()
