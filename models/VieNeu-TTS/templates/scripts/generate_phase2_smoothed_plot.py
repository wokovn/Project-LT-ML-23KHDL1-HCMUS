#!/usr/bin/env python3
"""Generate a smoothed Phase 2 learning curve (EMA, no raw lines)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate smoothed Phase 2 loss curve with EMA")
    parser.add_argument(
        "--state-path",
        default="runs/vieneu_tts/20260419_vieneu_transcript_phase2_full/phase2/checkpoints/checkpoint-23160/trainer_state.json",
    )
    parser.add_argument(
        "--output-path",
        default="runs/vieneu_tts/20260419_vieneu_transcript_phase2_full/phase2/metrics/figure_full_phase2_loss_curve.png",
    )
    parser.add_argument("--alpha", type=float, default=0.7, help="EMA coefficient, recommended range [0.6, 0.8]")
    return parser.parse_args()


def ema(values: list[float], alpha: float) -> list[float]:
    if not values:
        return []
    smoothed = [values[0]]
    prev = values[0]
    for v in values[1:]:
        prev = alpha * v + (1.0 - alpha) * prev
        smoothed.append(prev)
    return smoothed


def parse_state(state_path: Path):
    data = json.loads(state_path.read_text(encoding="utf-8"))
    train = []
    evals = []
    for item in data.get("log_history", []):
        if "loss" in item and "step" in item:
            train.append((int(item["step"]), float(item["loss"])))
        if "eval_loss" in item and "step" in item:
            evals.append((int(item["step"]), float(item["eval_loss"])))

    train.sort(key=lambda x: x[0])
    evals.sort(key=lambda x: x[0])
    return train, evals


def main() -> None:
    args = parse_args()
    if not (0.0 < args.alpha < 1.0):
        raise ValueError("--alpha must be in (0, 1)")

    state_path = Path(args.state_path)
    output_path = Path(args.output_path)

    if not state_path.exists():
        raise FileNotFoundError(f"trainer_state not found: {state_path}")

    train_points, eval_points = parse_state(state_path)
    if not train_points and not eval_points:
        raise RuntimeError("No train/eval points found in trainer_state")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 5.5))

    if train_points:
        tx = [p[0] for p in train_points]
        ty = [p[1] for p in train_points]
        ty_ema = ema(ty, args.alpha)
        plt.plot(tx, ty_ema, label=f"Train loss (EMA, alpha={args.alpha:.1f})", linewidth=2.0)

    if eval_points:
        ex = [p[0] for p in eval_points]
        ey = [p[1] for p in eval_points]
        ey_ema = ema(ey, args.alpha)
        plt.plot(ex, ey_ema, label=f"Validation loss (EMA, alpha={args.alpha:.1f})", linewidth=2.0, marker="o", markersize=3)

    plt.title("Full Phase 2 Learning Curve (Smoothed)")
    plt.xlabel("Step")
    plt.ylabel("Loss")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()

    print(f"state_path={state_path}")
    print(f"train_points={len(train_points)}")
    print(f"eval_points={len(eval_points)}")
    print(f"alpha={args.alpha}")
    print(f"output_figure={output_path}")


if __name__ == "__main__":
    main()
