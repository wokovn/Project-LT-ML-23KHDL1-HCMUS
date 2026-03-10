import csv
import random
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR  = PROJECT_ROOT / "data" / "dataset_2"


def split_metadata(
    src: Path,
    train_dst: Path,
    test_dst: Path,
    train_ratio: float = 0.8,
    seed: int = 42,
) -> tuple[int, int]:
    """Shuffle and split *src* CSV into train / test files.

    The header row is preserved in both output files.
    Rows are shuffled with *seed* for reproducibility.

    Args:
        src:         Path to the source metadata CSV.
        train_dst:   Destination path for the training split.
        test_dst:    Destination path for the test split.
        train_ratio: Fraction of rows assigned to training (default 0.8).
        seed:        Random seed for reproducibility (default 42).

    Returns:
        Tuple of (n_train, n_test) row counts (excluding header).
    """
    with open(src, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows   = list(reader)

    random.seed(seed)
    random.shuffle(rows)

    split_idx = int(len(rows) * train_ratio)
    train_rows = rows[:split_idx]
    test_rows  = rows[split_idx:]

    def write_csv(path: Path, data: list) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(header)
            writer.writerows(data)

    write_csv(train_dst, train_rows)
    write_csv(test_dst,  test_rows)

    return len(train_rows), len(test_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Split metadata.csv into train/test sets.")
    parser.add_argument("--seed",  type=int,   default=42,  help="Random seed (default: 42)")
    parser.add_argument("--ratio", type=float, default=0.8, help="Train ratio (default: 0.8)")
    args = parser.parse_args()

    src       = DATASET_DIR / "metadata.csv"
    train_dst = DATASET_DIR / "train.csv"
    test_dst  = DATASET_DIR / "test.csv"

    if not src.exists():
        print(f"[ERROR] Source file not found: {src}")
        raise SystemExit(1)

    print(f"Source : {src}")
    print(f"Ratio  : {args.ratio:.0%} train / {1 - args.ratio:.0%} test  (seed={args.seed})")

    n_train, n_test = split_metadata(
        src, train_dst, test_dst,
        train_ratio=args.ratio,
        seed=args.seed,
    )

    total = n_train + n_test
    print(f"\nDone!")
    print(f"  train.csv : {n_train:>5} rows  ({n_train / total:.1%})")
    print(f"  test.csv  : {n_test:>5} rows  ({n_test  / total:.1%})")
    print(f"  Total     : {total:>5} rows")
    print(f"\nOutput: {DATASET_DIR.resolve()}")


if __name__ == "__main__":
    main()
