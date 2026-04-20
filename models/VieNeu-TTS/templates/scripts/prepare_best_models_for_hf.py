#!/usr/bin/env python3
"""Prepare lightweight inference bundles for best checkpoints and HF upload."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


PHASE_TO_CHECKPOINT = {
    "phase1_best": "runs/vieneu_tts/20260419_vieneu_transcript_phase1_full/phase1/checkpoints/checkpoint-8000",
    "phase2_best": "runs/vieneu_tts/20260419_vieneu_transcript_phase2_full/phase2/checkpoints/checkpoint-15500",
    "phase3_best": "runs/vieneu_tts/20260420_vieneu_transcript_phase3_refine_retry1/phase3/checkpoints/checkpoint-17000",
}

# Keep only files required for inference portability.
REQUIRED_FILES = [
    "model.safetensors",
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "merges.txt",
    "added_tokens.json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare best model bundles for Hugging Face")
    parser.add_argument(
        "--output-root",
        default="models/VieNeu-TTS/resource/hf_best_models",
        help="Destination folder for phase bundles",
    )
    return parser.parse_args()


def copy_required_files(src_dir: Path, dst_dir: Path) -> list[str]:
    copied: list[str] = []
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_FILES:
        src = src_dir / name
        if src.exists():
            shutil.copy2(src, dst_dir / name)
            copied.append(name)
    return copied


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, dict[str, object]] = {}

    for phase, src in PHASE_TO_CHECKPOINT.items():
        src_dir = Path(src)
        if not src_dir.exists():
            raise FileNotFoundError(f"missing checkpoint directory: {src_dir}")

        dst_dir = output_root / phase
        copied = copy_required_files(src_dir, dst_dir)
        missing = [name for name in REQUIRED_FILES if name not in copied]

        model_path = dst_dir / "model.safetensors"
        model_size_bytes = model_path.stat().st_size if model_path.exists() else 0

        manifest[phase] = {
            "source_checkpoint": str(src_dir),
            "output_dir": str(dst_dir),
            "copied_files": copied,
            "missing_files": missing,
            "model_safetensors_size_bytes": model_size_bytes,
        }

        print(f"phase={phase} copied={len(copied)} missing={len(missing)}")

    manifest_path = output_root / "hf_bundle_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    readme = output_root / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# HF best model bundles",
                "",
                "This directory contains inference-only bundles for the three best checkpoints.",
                "Training states such as optimizer/scheduler/trainer_state are intentionally excluded.",
                "",
                "Subdirectories:",
                "- phase1_best",
                "- phase2_best",
                "- phase3_best",
                "",
                "See hf_bundle_manifest.json for source and file details.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"manifest={manifest_path}")
    print(f"readme={readme}")


if __name__ == "__main__":
    main()
