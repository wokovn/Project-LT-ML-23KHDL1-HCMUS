#!/usr/bin/env python3
"""Create deterministic smoke-test subsets from train/eval CSV files."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sample_rows(rows: list[dict[str, str]], n: int, seed: int) -> list[dict[str, str]]:
    if n <= 0:
        raise ValueError("n must be > 0")
    rng = random.Random(seed)
    copied = rows.copy()
    rng.shuffle(copied)
    return copied[: min(n, len(copied))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create smoke subsets for quick training checks")
    parser.add_argument("--train-csv", required=True, type=Path)
    parser.add_argument("--eval-csv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--train-n", type=int, default=64)
    parser.add_argument("--eval-n", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260419)
    args = parser.parse_args()

    train_fields, train_rows = read_csv_rows(args.train_csv)
    eval_fields, eval_rows = read_csv_rows(args.eval_csv)

    sampled_train = sample_rows(train_rows, args.train_n, args.seed)
    sampled_eval = sample_rows(eval_rows, args.eval_n, args.seed + 1)

    train_out = args.output_dir / "train_smoke.csv"
    eval_out = args.output_dir / "eval_smoke.csv"

    write_csv_rows(train_out, train_fields, sampled_train)
    write_csv_rows(eval_out, eval_fields, sampled_eval)

    print(f"Wrote {len(sampled_train)} rows -> {train_out}")
    print(f"Wrote {len(sampled_eval)} rows -> {eval_out}")


if __name__ == "__main__":
    main()
