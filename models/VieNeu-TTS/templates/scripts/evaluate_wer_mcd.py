#!/usr/bin/env python3
"""Evaluate MCD, DTW (MFCC), and F0 RMSE for TTS outputs.

Usage examples:

1) Build pairs from test CSV + generated audio directory:
   python models/VieNeu-TTS/templates/scripts/evaluate_wer_mcd.py \
     --test-csv data/xtts_stage2_24k_mono/test_wav.csv \
     --generated-dir runs/vieneu_tts/<RUN_TAG>/phase3/infer_test \
     --data-root data/xtts_stage2_24k_mono \
     --output-json runs/vieneu_tts/<RUN_TAG>/phase3/metrics/test_eval_metrics.json

2) Use prepared manifest CSV (columns: generated_wav, reference_wav):
   python models/VieNeu-TTS/templates/scripts/evaluate_wer_mcd.py \
     --manifest-csv path/to/manifest.csv \
     --output-json path/to/test_eval_metrics.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import wave
from dataclasses import dataclass
from pathlib import Path

AUDIO_COL_CANDIDATES = ["audio_file", "wav", "wav_path", "audio_path", "path", "file"]
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}


@dataclass
class EvalItem:
    utt_id: str
    reference_wav: Path
    generated_wav: Path


def _detect_delimiter(first_line: str) -> str:
    for cand in ("|", ",", ";", "\t"):
        if cand in first_line:
            return cand
    return ","


def _read_csv(csv_path: Path, delimiter: str | None = None) -> list[dict[str, str]]:
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
    raise ValueError(f"No matching column found from {candidates}. Available: {fieldnames}")


def _resolve_from_manifest(path_value: str, manifest_path: Path) -> Path:
    p = Path(path_value)
    if p.is_absolute():
        return p

    manifest_relative = (manifest_path.parent / p).resolve()
    if manifest_relative.exists():
        return manifest_relative

    return (Path.cwd() / p).resolve()


def _build_generated_index(generated_dir: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    by_rel: dict[str, Path] = {}
    by_stem: dict[str, Path] = {}
    for wav in generated_dir.rglob("*"):
        if not wav.is_file() or wav.suffix.lower() not in AUDIO_EXTS:
            continue
        rel_key = wav.relative_to(generated_dir).as_posix()
        by_rel[rel_key] = wav
        if wav.stem not in by_stem:
            by_stem[wav.stem] = wav
    return by_rel, by_stem


def _resolve_generated(audio_value: str, generated_dir: Path, by_rel: dict[str, Path], by_stem: dict[str, Path]) -> Path | None:
    p = Path(audio_value)
    candidates = [
        generated_dir / audio_value,
        generated_dir / p.name,
        generated_dir / f"{p.stem}.wav",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()

    rel_key = audio_value.replace("\\", "/")
    if rel_key in by_rel:
        return by_rel[rel_key].resolve()

    if p.stem in by_stem:
        return by_stem[p.stem].resolve()

    return None


def _load_wav_pcm(wav_path: Path):
    import numpy as np
    import torch

    with wave.open(wav_path.as_posix(), "rb") as wf:
        sr = wf.getframerate()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 1:
        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        arr = (arr - 128.0) / 128.0
    elif sampwidth == 2:
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        val = (
            b[:, 0].astype(np.int32)
            | (b[:, 1].astype(np.int32) << 8)
            | (b[:, 2].astype(np.int32) << 16)
        )
        sign_mask = 1 << 23
        val = (val ^ sign_mask) - sign_mask
        arr = val.astype(np.float32) / 8388608.0
    elif sampwidth == 4:
        arr = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported PCM sample width: {sampwidth}")

    if n_channels <= 0:
        raise ValueError("invalid channel count")
    if arr.size % n_channels != 0:
        raise ValueError("corrupted wav frame layout")

    arr = arr.reshape(-1, n_channels).T  # [C, T]
    wav_tensor = torch.from_numpy(arr)
    return wav_tensor, sr


def _load_audio_mono_resampled(wav_path: Path, sample_rate: int):
    import numpy as np
    import torchaudio

    try:
        wav, sr = torchaudio.load(wav_path.as_posix())
    except Exception:
        wav, sr = _load_wav_pcm(wav_path)

    if wav.numel() == 0:
        raise ValueError("empty waveform")
    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    if sr != sample_rate:
        wav = torchaudio.functional.resample(wav, sr, sample_rate)
    return wav.squeeze(0).cpu().numpy().astype(np.float32)


def _to_time_major(features):
    # [D, T] -> [T, D]
    return features.T.copy()


def _downsample_time_frames(x, max_frames: int):
    if max_frames <= 0:
        return x
    if x.shape[0] <= max_frames:
        return x
    stride = int(math.ceil(x.shape[0] / max_frames))
    return x[::stride]


def _dtw_path_and_mean_cost(ref_seq, gen_seq):
    import numpy as np

    if ref_seq.ndim == 1:
        ref_seq = ref_seq[:, None]
    if gen_seq.ndim == 1:
        gen_seq = gen_seq[:, None]

    n = ref_seq.shape[0]
    m = gen_seq.shape[0]
    if n == 0 or m == 0:
        raise ValueError("empty DTW input")

    inf = np.inf
    cost = np.full((n + 1, m + 1), inf, dtype=np.float64)
    back = np.zeros((n + 1, m + 1), dtype=np.uint8)
    cost[0, 0] = 0.0

    for i in range(1, n + 1):
        diff = gen_seq - ref_seq[i - 1][None, :]
        local = np.linalg.norm(diff, axis=1)
        for j in range(1, m + 1):
            up = cost[i - 1, j]
            left = cost[i, j - 1]
            diag = cost[i - 1, j - 1]

            if diag <= up and diag <= left:
                best = diag
                back[i, j] = 3
            elif up <= left:
                best = up
                back[i, j] = 1
            else:
                best = left
                back[i, j] = 2

            cost[i, j] = local[j - 1] + best

    i, j = n, m
    path = []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        move = back[i, j]
        if move == 3:
            i -= 1
            j -= 1
        elif move == 1:
            i -= 1
        elif move == 2:
            j -= 1
        else:
            break

    while i > 0:
        i -= 1
        path.append((i, 0))
    while j > 0:
        j -= 1
        path.append((0, j))

    path.reverse()
    if not path:
        raise ValueError("empty DTW path")

    mean_cost = float(cost[n, m] / len(path))
    return path, mean_cost


def _extract_mfcc(y, sample_rate: int, n_mfcc: int, n_fft: int, hop_length: int, drop_c0: bool):
    import torch
    import torchaudio

    n_mels = max(40, n_mfcc * 2)
    transform = torchaudio.transforms.MFCC(
        sample_rate=sample_rate,
        n_mfcc=n_mfcc,
        melkwargs={
            "n_fft": n_fft,
            "hop_length": hop_length,
            "n_mels": n_mels,
            "center": True,
            "power": 2.0,
        },
    )

    with torch.no_grad():
        feat = transform(torch.from_numpy(y).unsqueeze(0))  # [1, n_mfcc, T]
    feat_np = feat.squeeze(0).cpu().numpy()
    if feat_np.ndim != 2 or feat_np.shape[1] == 0:
        raise ValueError("empty MFCC frames")
    if drop_c0 and feat_np.shape[0] > 1:
        feat_np = feat_np[1:, :]
    return _to_time_major(feat_np)


def _extract_f0_track(y, sample_rate: int, hop_length: int, f0_min_hz: float, f0_max_hz: float):
    import torch
    import torchaudio

    frame_time = max(1.0 / sample_rate, hop_length / float(sample_rate))
    waveform = torch.from_numpy(y).unsqueeze(0)
    with torch.no_grad():
        f0 = torchaudio.functional.detect_pitch_frequency(
            waveform=waveform,
            sample_rate=sample_rate,
            frame_time=frame_time,
            freq_low=float(f0_min_hz),
            freq_high=float(f0_max_hz),
        )
    return f0.squeeze(0).cpu().numpy().astype("float32")


def _compute_metrics_for_pair(
    reference_wav: Path,
    generated_wav: Path,
    sample_rate: int,
    n_mfcc: int,
    n_fft: int,
    hop_length: int,
    drop_c0: bool,
    max_frames_mfcc: int,
    max_frames_f0: int,
    f0_min_hz: float,
    f0_max_hz: float,
):
    import numpy as np

    y_ref = _load_audio_mono_resampled(reference_wav, sample_rate)
    y_gen = _load_audio_mono_resampled(generated_wav, sample_rate)

    mfcc_ref = _extract_mfcc(y_ref, sample_rate, n_mfcc, n_fft, hop_length, drop_c0)
    mfcc_gen = _extract_mfcc(y_gen, sample_rate, n_mfcc, n_fft, hop_length, drop_c0)
    mfcc_ref = _downsample_time_frames(mfcc_ref, max_frames_mfcc)
    mfcc_gen = _downsample_time_frames(mfcc_gen, max_frames_mfcc)

    _, dtw_mfcc = _dtw_path_and_mean_cost(mfcc_ref, mfcc_gen)
    mcd_scale = (10.0 / np.log(10.0)) * np.sqrt(2.0)
    mcd_db = float(mcd_scale * dtw_mfcc)

    f0_ref = _extract_f0_track(y_ref, sample_rate, hop_length, f0_min_hz, f0_max_hz)
    f0_gen = _extract_f0_track(y_gen, sample_rate, hop_length, f0_min_hz, f0_max_hz)
    f0_ref = _downsample_time_frames(f0_ref, max_frames_f0)
    f0_gen = _downsample_time_frames(f0_gen, max_frames_f0)

    voiced_ref = f0_ref[f0_ref > 0.0]
    voiced_gen = f0_gen[f0_gen > 0.0]
    if voiced_ref.size == 0 or voiced_gen.size == 0:
        raise ValueError("no voiced frames for F0 RMSE")

    log_ref = np.log(voiced_ref)
    log_gen = np.log(voiced_gen)
    f0_path, dtw_f0_log = _dtw_path_and_mean_cost(log_ref, log_gen)

    sq_err = []
    for i, j in f0_path:
        d = float(voiced_ref[i] - voiced_gen[j])
        sq_err.append(d * d)
    if not sq_err:
        raise ValueError("empty aligned voiced pairs")

    f0_rmse_hz = float(np.sqrt(np.mean(sq_err)))

    return {
        "mcd_db": mcd_db,
        "dtw_mfcc": float(dtw_mfcc),
        "f0_rmse_hz": f0_rmse_hz,
        "dtw_f0_log": float(dtw_f0_log),
        "voiced_pairs": len(f0_path),
    }


def _build_items_from_manifest(args: argparse.Namespace) -> list[EvalItem]:
    manifest_csv = Path(args.manifest_csv)
    if not manifest_csv.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_csv}")

    rows = _read_csv(manifest_csv, delimiter=args.manifest_delimiter)
    if not rows:
        return []

    fieldnames = list(rows[0].keys())
    gen_col = _detect_column(fieldnames, ["generated_wav", "gen_wav", "pred_wav"], args.manifest_generated_wav_col)
    ref_col = _detect_column(fieldnames, ["reference_wav", "ref_wav", "gt_wav"], args.manifest_reference_wav_col)

    utt_id_col = args.manifest_utt_id_col if args.manifest_utt_id_col in fieldnames else None

    items: list[EvalItem] = []
    for i, row in enumerate(rows, start=1):
        ref_wav = _resolve_from_manifest(row.get(ref_col, ""), manifest_csv)
        gen_wav = _resolve_from_manifest(row.get(gen_col, ""), manifest_csv)

        if utt_id_col:
            utt_id = (row.get(utt_id_col, "") or "").strip() or f"utt_{i:06d}"
        else:
            utt_id = gen_wav.stem if gen_wav.stem else f"utt_{i:06d}"

        items.append(EvalItem(utt_id=utt_id, reference_wav=ref_wav, generated_wav=gen_wav))
    return items


def _build_items_from_test_csv(args: argparse.Namespace) -> list[EvalItem]:
    test_csv = Path(args.test_csv)
    generated_dir = Path(args.generated_dir)
    data_root = Path(args.data_root)

    if not test_csv.exists():
        raise FileNotFoundError(f"test csv not found: {test_csv}")
    if not generated_dir.exists():
        raise FileNotFoundError(f"generated dir not found: {generated_dir}")

    rows = _read_csv(test_csv, delimiter=args.test_delimiter)
    if not rows:
        return []

    fieldnames = list(rows[0].keys())
    audio_col = _detect_column(fieldnames, AUDIO_COL_CANDIDATES, args.test_audio_col)

    by_rel, by_stem = _build_generated_index(generated_dir)

    items: list[EvalItem] = []
    for row in rows:
        audio_value = (row.get(audio_col, "") or "").strip()
        if not audio_value:
            continue

        rel_audio = Path(audio_value)
        ref_wav = rel_audio if rel_audio.is_absolute() else (data_root / rel_audio)
        gen_wav = _resolve_generated(audio_value, generated_dir, by_rel, by_stem)
        if gen_wav is None:
            gen_wav = generated_dir / f"{rel_audio.stem}.wav"

        items.append(EvalItem(utt_id=rel_audio.stem, reference_wav=ref_wav.resolve(), generated_wav=gen_wav))

    return items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute MCD, DTW and F0 RMSE for TTS outputs")

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--manifest-csv", default=None)
    input_group.add_argument("--test-csv", default=None)

    parser.add_argument("--generated-dir", default=None, help="Required when using --test-csv")
    parser.add_argument("--data-root", default="data/xtts_stage2_24k_mono")

    parser.add_argument("--manifest-delimiter", default=None)
    parser.add_argument("--manifest-utt-id-col", default="utt_id")
    parser.add_argument("--manifest-generated-wav-col", default=None)
    parser.add_argument("--manifest-reference-wav-col", default=None)

    parser.add_argument("--test-delimiter", default=None)
    parser.add_argument("--test-audio-col", default=None)

    parser.add_argument("--sample-rate", type=int, default=24000)
    parser.add_argument("--n-mfcc", type=int, default=14, help="Including C0")
    parser.add_argument("--n-fft", type=int, default=1024)
    parser.add_argument("--hop-length", type=int, default=480)
    parser.add_argument("--keep-c0", action="store_true", help="Keep C0 coefficient in MCD")
    parser.add_argument("--max-frames-mfcc", type=int, default=1200)
    parser.add_argument("--max-frames-f0", type=int, default=1600)
    parser.add_argument("--f0-min-hz", type=float, default=50.0)
    parser.add_argument("--f0-max-hz", type=float, default=550.0)

    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", default=None)

    return parser.parse_args()


def _agg(values):
    if not values:
        return {"mean": None, "std": None, "median": None}
    if len(values) == 1:
        return {"mean": float(values[0]), "std": 0.0, "median": float(values[0])}
    return {
        "mean": float(statistics.mean(values)),
        "std": float(statistics.pstdev(values)),
        "median": float(statistics.median(values)),
    }


def main() -> None:
    args = parse_args()

    try:
        from tqdm import tqdm
    except Exception as exc:
        raise RuntimeError("Missing dependency tqdm. Install requirements from models/VieNeu-TTS/requirements.txt") from exc

    if args.test_csv and not args.generated_dir:
        raise ValueError("--generated-dir is required when using --test-csv")

    if args.manifest_csv:
        items = _build_items_from_manifest(args)
    else:
        items = _build_items_from_test_csv(args)

    if args.limit > 0:
        items = items[: args.limit]

    if not items:
        raise RuntimeError("No evaluation items found.")

    drop_c0 = not args.keep_c0

    rows_out = []
    mcd_vals = []
    dtw_vals = []
    f0_vals = []
    dtw_f0_vals = []

    for item in tqdm(items, desc="Evaluating", unit="utt"):
        errors = []
        mcd_db = None
        dtw_mfcc = None
        f0_rmse_hz = None
        dtw_f0_log = None
        voiced_pairs = None

        if not item.reference_wav.exists():
            errors.append(f"missing reference wav: {item.reference_wav}")
        if not item.generated_wav.exists():
            errors.append(f"missing generated wav: {item.generated_wav}")

        if not errors:
            try:
                metrics = _compute_metrics_for_pair(
                    reference_wav=item.reference_wav,
                    generated_wav=item.generated_wav,
                    sample_rate=args.sample_rate,
                    n_mfcc=args.n_mfcc,
                    n_fft=args.n_fft,
                    hop_length=args.hop_length,
                    drop_c0=drop_c0,
                    max_frames_mfcc=args.max_frames_mfcc,
                    max_frames_f0=args.max_frames_f0,
                    f0_min_hz=args.f0_min_hz,
                    f0_max_hz=args.f0_max_hz,
                )
                mcd_db = metrics["mcd_db"]
                dtw_mfcc = metrics["dtw_mfcc"]
                f0_rmse_hz = metrics["f0_rmse_hz"]
                dtw_f0_log = metrics["dtw_f0_log"]
                voiced_pairs = metrics["voiced_pairs"]

                mcd_vals.append(mcd_db)
                dtw_vals.append(dtw_mfcc)
                f0_vals.append(f0_rmse_hz)
                dtw_f0_vals.append(dtw_f0_log)
            except Exception as exc:
                errors.append(f"metric_error: {exc}")

        has_any_metric = any(v is not None for v in (mcd_db, dtw_mfcc, f0_rmse_hz))
        status = "ok" if not errors else ("partial" if has_any_metric else "error")

        rows_out.append(
            {
                "utt_id": item.utt_id,
                "reference_wav": item.reference_wav.as_posix(),
                "generated_wav": item.generated_wav.as_posix(),
                "mcd_db": mcd_db,
                "dtw_mfcc": dtw_mfcc,
                "f0_rmse_hz": f0_rmse_hz,
                "dtw_f0_log": dtw_f0_log,
                "voiced_pairs": voiced_pairs,
                "status": status,
                "error": " | ".join(errors),
            }
        )

    mcd_agg = _agg(mcd_vals)
    dtw_agg = _agg(dtw_vals)
    f0_agg = _agg(f0_vals)
    dtw_f0_agg = _agg(dtw_f0_vals)

    summary = {
        "num_items": len(items),
        "num_ok": sum(1 for r in rows_out if r["status"] == "ok"),
        "num_partial": sum(1 for r in rows_out if r["status"] == "partial"),
        "num_error": sum(1 for r in rows_out if r["status"] == "error"),
        "mcd_db_mean": mcd_agg["mean"],
        "mcd_db_std": mcd_agg["std"],
        "mcd_db_median": mcd_agg["median"],
        "dtw_mfcc_mean": dtw_agg["mean"],
        "dtw_mfcc_std": dtw_agg["std"],
        "dtw_mfcc_median": dtw_agg["median"],
        "f0_rmse_hz_mean": f0_agg["mean"],
        "f0_rmse_hz_std": f0_agg["std"],
        "f0_rmse_hz_median": f0_agg["median"],
        "dtw_f0_log_mean": dtw_f0_agg["mean"],
        "dtw_f0_log_std": dtw_f0_agg["std"],
        "dtw_f0_log_median": dtw_f0_agg["median"],
        "sample_rate": args.sample_rate,
        "n_mfcc": args.n_mfcc,
        "n_fft": args.n_fft,
        "hop_length": args.hop_length,
        "drop_c0": drop_c0,
        "f0_min_hz": args.f0_min_hz,
        "f0_max_hz": args.f0_max_hz,
        "max_frames_mfcc": args.max_frames_mfcc,
        "max_frames_f0": args.max_frames_f0,
    }

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    output_csv = Path(args.output_csv) if args.output_csv else output_json.with_name(output_json.stem + "_per_utt.csv")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "utt_id",
        "reference_wav",
        "generated_wav",
        "mcd_db",
        "dtw_mfcc",
        "f0_rmse_hz",
        "dtw_f0_log",
        "voiced_pairs",
        "status",
        "error",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"summary_json={output_json}")
    print(f"per_utt_csv={output_csv}")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
