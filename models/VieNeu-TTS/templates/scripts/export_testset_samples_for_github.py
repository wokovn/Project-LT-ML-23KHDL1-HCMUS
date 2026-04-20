#!/usr/bin/env python3
"""Export a small random subset of generated/reference test audio for GitHub."""

from __future__ import annotations

import argparse
import csv
import random
import shutil
import wave
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export random test-set samples for GitHub")
    parser.add_argument(
        "--eval-root",
        default="runs/vieneu_tts/20260420_testset_eval_best3",
        help="Root folder containing phase*_best generated outputs",
    )
    parser.add_argument(
        "--reference-wavs-dir",
        default="data/xtts_stage2_24k_mono/wavs",
        help="Reference wav directory",
    )
    parser.add_argument(
        "--output-root",
        default="models/VieNeu-TTS/resource/github_testset_samples",
        help="Output folder for selected samples",
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        default=["phase1_best", "phase2_best", "phase3_best"],
        help="Phase folders under eval root",
    )
    parser.add_argument("--samples-per-phase", type=int, default=12, help="Number of random samples per phase")
    parser.add_argument("--seed", type=int, default=20260420, help="Random seed")
    return parser.parse_args()


def duration_sec(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        sr = wf.getframerate()
    if sr <= 0:
        return 0.0
    return frames / float(sr)


def main() -> None:
    args = parse_args()

    eval_root = Path(args.eval_root)
    reference_wavs_dir = Path(args.reference_wavs_dir)
    output_root = Path(args.output_root)

    if not eval_root.exists():
        raise FileNotFoundError(f"eval root not found: {eval_root}")
    if not reference_wavs_dir.exists():
        raise FileNotFoundError(f"reference wav dir not found: {reference_wavs_dir}")
    if args.samples_per_phase <= 0:
        raise ValueError("--samples-per-phase must be > 0")

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    rows: list[dict[str, str]] = []

    for idx, phase in enumerate(args.phases):
        phase_generated_dir = eval_root / phase / "generated" / "wavs"
        if not phase_generated_dir.exists():
            raise FileNotFoundError(f"generated wav dir not found: {phase_generated_dir}")

        candidates = sorted(phase_generated_dir.glob("*.wav"))
        pairs: list[tuple[Path, Path]] = []
        for gen_wav in candidates:
            ref_wav = reference_wavs_dir / gen_wav.name
            if ref_wav.exists():
                pairs.append((gen_wav, ref_wav))

        if not pairs:
            raise RuntimeError(f"no generated/reference wav pairs found for {phase}")

        n = min(args.samples_per_phase, len(pairs))
        phase_rng = random.Random(args.seed + idx)
        selected = phase_rng.sample(pairs, n)

        out_gen_dir = output_root / phase / "generated"
        out_ref_dir = output_root / phase / "reference"
        out_gen_dir.mkdir(parents=True, exist_ok=True)
        out_ref_dir.mkdir(parents=True, exist_ok=True)

        for gen_wav, ref_wav in sorted(selected, key=lambda x: x[0].name):
            utt_id = gen_wav.stem
            out_gen = out_gen_dir / gen_wav.name
            out_ref = out_ref_dir / ref_wav.name

            shutil.copy2(gen_wav, out_gen)
            shutil.copy2(ref_wav, out_ref)

            rows.append(
                {
                    "phase": phase,
                    "utt_id": utt_id,
                    "generated_file": str(out_gen.relative_to(output_root)),
                    "reference_file": str(out_ref.relative_to(output_root)),
                    "generated_duration_sec": f"{duration_sec(out_gen):.4f}",
                    "reference_duration_sec": f"{duration_sec(out_ref):.4f}",
                }
            )

        print(f"phase={phase} total_pairs={len(pairs)} selected={n}")

    manifest_path = output_root / "selection_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "phase",
                "utt_id",
                "generated_file",
                "reference_file",
                "generated_duration_sec",
                "reference_duration_sec",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    readme_path = output_root / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                "# GitHub test-set samples",
                "",
                "This folder contains a small random subset of generated and reference wav files,",
                "intended for quick qualitative listening checks in GitHub.",
                "",
                f"- phases: {', '.join(args.phases)}",
                f"- samples_per_phase: {args.samples_per_phase}",
                f"- seed: {args.seed}",
                f"- manifest: {manifest_path.name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"manifest={manifest_path}")
    print(f"readme={readme_path}")
    print(f"output_root={output_root}")


if __name__ == "__main__":
    main()
