#!/usr/bin/env python3
"""Generate smoke/full Phase 1 learning-curve plots from training logs."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import matplotlib.pyplot as plt


def parse_log(log_path: Path):
    train_points = []
    eval_points = []
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            d = ast.literal_eval(line)
        except Exception:
            continue
        if "loss" in d and "epoch" in d:
            # Keep numeric dict entries that are actual train logs
            if isinstance(d.get("loss"), (int, float)):
                train_points.append((float(d["epoch"]), float(d["loss"])))
        if "eval_loss" in d and "epoch" in d:
            if isinstance(d.get("eval_loss"), (int, float)):
                eval_points.append((float(d["epoch"]), float(d["eval_loss"])))
    return train_points, eval_points


def parse_trainer_state(state_path: Path):
    train_points = []
    eval_points = []
    data = json.loads(state_path.read_text(encoding="utf-8"))
    for item in data.get("log_history", []):
        if "loss" in item and "epoch" in item:
            train_points.append((float(item["epoch"]), float(item["loss"])))
        if "eval_loss" in item and "epoch" in item:
            eval_points.append((float(item["epoch"]), float(item["eval_loss"])))
    return train_points, eval_points


def plot_curve(train_points, eval_points, title: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(9, 5))
    if train_points:
        x, y = zip(*train_points)
        plt.plot(x, y, label="Train loss", linewidth=1.5)
    if eval_points:
        ex, ey = zip(*eval_points)
        plt.plot(ex, ey, label="Validation loss", marker="o", linewidth=1.5)
    plt.title(title)
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def main():
    root = Path("runs/vieneu_tts")

    smoke_log = root / "20260419_vieneu_transcript_smoke_bf16" / "phase1_train.log"
    smoke_out = root / "20260419_vieneu_transcript_smoke_bf16" / "phase1" / "metrics" / "figure_smoke_phase1_loss_curve.png"

    full_log = root / "20260419_vieneu_transcript_phase1_full" / "phase1_train.log"
    full_out = root / "20260419_vieneu_transcript_phase1_full" / "phase1" / "metrics" / "figure_full_phase1_loss_curve.png"

    if smoke_log.exists():
        st, se = parse_log(smoke_log)
    else:
        smoke_state = root / "20260419_vieneu_transcript_smoke_bf16" / "phase1" / "checkpoints" / "checkpoint-100" / "trainer_state.json"
        st, se = parse_trainer_state(smoke_state)

    if full_log.exists():
        ft, fe = parse_log(full_log)
    else:
        full_state = root / "20260419_vieneu_transcript_phase1_full" / "phase1" / "checkpoints" / "checkpoint-8685" / "trainer_state.json"
        ft, fe = parse_trainer_state(full_state)

    plot_curve(st, se, "Smoke Phase 1 Learning Curve", smoke_out)
    plot_curve(ft, fe, "Full Phase 1 Learning Curve", full_out)

    print(f"smoke_points_train={len(st)} eval={len(se)}")
    print(f"full_points_train={len(ft)} eval={len(fe)}")
    print(f"smoke_figure={smoke_out}")
    print(f"full_figure={full_out}")


if __name__ == "__main__":
    main()
