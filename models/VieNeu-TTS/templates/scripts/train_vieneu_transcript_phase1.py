#!/usr/bin/env python3
"""Phase 1 transcript-based training entrypoint for VieNeu-style data.

This script is intentionally compatible with run_phase1_warmup.sh arguments.
It trains a causal LM on transcript prompts (text-only objective) and writes
training/eval metrics into the phase output metrics directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Iterable

import torch
import yaml
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    default_data_collator,
    set_seed,
)

TEXT_COL_CANDIDATES = ["text", "transcript", "sentence", "normalized_text"]


def _detect_delimiter(line: str) -> str:
    for candidate in ("|", ",", ";", "\t"):
        if candidate in line:
            return candidate
    return ","


def _detect_text_column(fieldnames: list[str]) -> str:
    lowered = {name.lower(): name for name in fieldnames}
    for key in TEXT_COL_CANDIDATES:
        if key in lowered:
            return lowered[key]
    raise ValueError(f"No text-like column found. Headers: {fieldnames}")


def _read_text_rows(csv_path: Path) -> list[str]:
    raw = csv_path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return []

    first_line = raw.splitlines()[0]
    delimiter = _detect_delimiter(first_line)
    reader = csv.DictReader(raw.splitlines(), delimiter=delimiter)
    if reader.fieldnames is None:
        return []

    text_col = _detect_text_column(list(reader.fieldnames))
    rows: list[str] = []
    for row in reader:
        text = (row.get(text_col) or "").strip()
        if text:
            rows.append(text)
    return rows


def _sample_rows(rows: list[str], limit: int, seed: int) -> list[str]:
    if limit <= 0 or len(rows) <= limit:
        return rows
    rng = random.Random(seed)
    selected = rows.copy()
    rng.shuffle(selected)
    return selected[:limit]


def _build_prompt(text: str) -> str:
    # Keep the prompt style aligned with VieNeu transcript instruction format.
    return (
        "user: Convert the text to speech:"
        f"<|TEXT_PROMPT_START|>{text}<|TEXT_PROMPT_END|>\n"
        f"assistant:<|SPEECH_GENERATION_START|>{text}<|SPEECH_GENERATION_END|>"
    )


class TranscriptDataset(Dataset):
    def __init__(self, texts: Iterable[str], tokenizer, max_length: int):
        self.examples = []
        for text in texts:
            prompt = _build_prompt(text)
            encoded = tokenizer(
                prompt,
                truncation=True,
                max_length=max_length,
                padding="max_length",
                return_attention_mask=True,
            )
            input_ids = torch.tensor(encoded["input_ids"], dtype=torch.long)
            attention_mask = torch.tensor(encoded["attention_mask"], dtype=torch.long)
            labels = input_ids.clone()
            labels[attention_mask == 0] = -100
            self.examples.append(
                {
                    "input_ids": input_ids,
                    "attention_mask": attention_mask,
                    "labels": labels,
                }
            )

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int):
        return self.examples[idx]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VieNeu transcript Phase 1 trainer")
    parser.add_argument("--config", required=True)
    parser.add_argument("--phase", default="phase1")
    parser.add_argument("--resume-from-checkpoint", default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=20260419)
    parser.add_argument("--mixed-precision", default="fp16")
    parser.add_argument("--save-top-k", type=int, default=3)
    parser.add_argument("--save-last", default="true")

    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--max-epoch", type=int, default=None)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--per-device-eval-batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=None)

    args, unknown = parser.parse_known_args()
    if unknown:
        print("Ignoring unknown args:", " ".join(unknown))
    return args


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    paths = cfg.get("paths", {})
    runtime = cfg.get("runtime", {})
    checkpointing = cfg.get("checkpointing", {})
    validation = cfg.get("validation", {})
    smoke_cfg = cfg.get("smoke_test", {})
    phase_cfg = cfg.get("phases", {}).get(args.phase, {})

    if args.resume_from_checkpoint:
        resume_path = Path(args.resume_from_checkpoint)
        if not resume_path.exists():
            raise FileNotFoundError(f"resume checkpoint not found: {resume_path}")

    output_dir = Path(args.output_dir)
    ckpt_dir = output_dir / "checkpoints"
    log_dir = output_dir / "logs"
    sample_dir = output_dir / "samples"
    metric_dir = output_dir / "metrics"
    for d in (ckpt_dir, log_dir, sample_dir, metric_dir):
        d.mkdir(parents=True, exist_ok=True)

    data_root = Path(paths.get("data_root", "data/xtts_stage2_24k_mono"))
    train_csv = data_root / paths.get("train_csv", "train_wav.csv")
    eval_csv = data_root / paths.get("eval_csv", "eval.csv")

    model_dir = Path(paths.get("pretrained_model_dir", "models/pretrained/VieNeu-TTS"))

    print(f"data_root={data_root}")
    print(f"train_csv={train_csv}")
    print(f"eval_csv={eval_csv}")
    print(f"model_dir={model_dir}")

    train_texts = _read_text_rows(train_csv)
    eval_texts = _read_text_rows(eval_csv) if eval_csv.exists() else []

    if not train_texts:
        raise RuntimeError(f"No valid training transcript rows in {train_csv}")

    is_smoke = args.max_steps is not None and args.max_steps > 0 and args.max_steps <= 200
    if is_smoke:
        train_limit = int(smoke_cfg.get("train_subset_size", 64))
        eval_limit = int(smoke_cfg.get("eval_subset_size", 16))
        train_texts = _sample_rows(train_texts, train_limit, args.seed)
        eval_texts = _sample_rows(eval_texts, eval_limit, args.seed + 1)

    print(f"train_rows={len(train_texts)}")
    print(f"eval_rows={len(eval_texts)}")

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    use_cuda = torch.cuda.is_available()
    # Qwen-style models can produce unstable FP16 gradients on long-context prompts.
    # Use BF16 as a safer default on Ampere+ GPUs even when wrapper asks for fp16.
    use_fp16 = False
    use_bf16 = use_cuda

    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        trust_remote_code=True,
        dtype=torch.bfloat16 if use_bf16 else torch.float32,
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.use_cache = False

    train_dataset = TranscriptDataset(train_texts, tokenizer, max_length=args.max_length)
    eval_dataset = TranscriptDataset(eval_texts, tokenizer, max_length=args.max_length) if eval_texts else None

    learning_rate = float(args.learning_rate if args.learning_rate is not None else phase_cfg.get("learning_rate", 1.0e-5))
    grad_accum = int(runtime.get("gradient_accumulation_steps", 4))
    eval_steps = int(validation.get("run_eval_every_n_steps", 500))
    save_steps = int(checkpointing.get("every_n_steps", 500))

    num_train_epochs = int(args.max_epoch if args.max_epoch is not None else phase_cfg.get("epochs", 3))
    max_steps = int(args.max_steps) if args.max_steps is not None else -1

    if is_smoke:
        eval_steps = max(10, min(50, max_steps // 2 if max_steps > 0 else 20))
        save_steps = eval_steps

    training_args = TrainingArguments(
        output_dir=str(ckpt_dir),
        overwrite_output_dir=True,
        do_train=True,
        do_eval=eval_dataset is not None and len(eval_dataset) > 0,
        eval_strategy="steps" if eval_dataset is not None and len(eval_dataset) > 0 else "no",
        eval_steps=eval_steps,
        save_strategy="steps",
        save_steps=save_steps,
        save_total_limit=max(1, args.save_top_k),
        load_best_model_at_end=eval_dataset is not None and len(eval_dataset) > 0,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        per_device_train_batch_size=max(1, args.per_device_train_batch_size),
        per_device_eval_batch_size=max(1, args.per_device_eval_batch_size),
        gradient_accumulation_steps=max(1, grad_accum),
        learning_rate=learning_rate,
        max_steps=max_steps,
        num_train_epochs=num_train_epochs,
        logging_steps=10,
        logging_dir=str(log_dir),
        report_to="none",
        fp16=use_fp16,
        bf16=use_bf16,
        dataloader_num_workers=2,
        remove_unused_columns=False,
        seed=args.seed,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=default_data_collator,
    )

    train_result = trainer.train(
        resume_from_checkpoint=args.resume_from_checkpoint if args.resume_from_checkpoint else None
    )
    eval_metrics = trainer.evaluate() if eval_dataset is not None and len(eval_dataset) > 0 else {}

    trainer.save_model(str(ckpt_dir / "final"))
    tokenizer.save_pretrained(str(ckpt_dir / "final"))

    metrics = {}
    metrics.update(train_result.metrics)
    metrics.update({f"eval_{k}": v for k, v in eval_metrics.items()})
    metrics.update(
        {
            "phase": args.phase,
            "train_rows": len(train_texts),
            "eval_rows": len(eval_texts),
            "learning_rate": learning_rate,
            "max_steps": max_steps,
            "num_train_epochs": num_train_epochs,
            "mixed_precision": args.mixed_precision,
            "cuda_available": use_cuda,
        }
    )

    metrics_path = metric_dir / f"{args.phase}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"metrics_file={metrics_path}")

    fixed_sentences_file = Path(paths.get("fixed_sentences_file", ""))
    if fixed_sentences_file.exists():
        lines = [line.strip() for line in fixed_sentences_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        lines = lines[:5]
        model.eval()
        generations = []
        for i, sentence in enumerate(lines, start=1):
            prompt = (
                "user: Convert the text to speech:"
                f"<|TEXT_PROMPT_START|>{sentence}<|TEXT_PROMPT_END|>\n"
                "assistant:<|SPEECH_GENERATION_START|>"
            )
            tok = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=args.max_length)
            tok = {k: v.to(model.device) for k, v in tok.items()}
            with torch.no_grad():
                out = model.generate(
                    **tok,
                    max_new_tokens=64,
                    do_sample=False,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id,
                )
            completion = out[0][tok["input_ids"].shape[1] :]
            text = tokenizer.decode(completion, skip_special_tokens=False)
            generations.append(f"[{i}] INPUT: {sentence}\n[{i}] OUTPUT: {text}\n")

        sample_path = sample_dir / f"{args.phase}_text_samples.txt"
        sample_path.write_text("\n".join(generations), encoding="utf-8")
        print(f"sample_file={sample_path}")

    print(f"{args.phase}_transcript_training_done")


if __name__ == "__main__":
    main()
