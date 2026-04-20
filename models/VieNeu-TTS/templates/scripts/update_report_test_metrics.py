#!/usr/bin/env python3
"""Update report with objective test-set metrics for phase1/2/3 best checkpoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


START_MARKER = "<!-- AUTO_TESTSET_METRICS_START -->"
END_MARKER = "<!-- AUTO_TESTSET_METRICS_END -->"


def fmt(v, digits=4):
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.{digits}f}"
    except Exception:
        return str(v)


def build_section(summary: dict, summary_path: Path) -> str:
    p1 = summary.get("phase1_best") or {}
    p2 = summary.get("phase2_best") or {}
    p3 = summary.get("phase3_best") or {}

    lines = []
    lines.append(START_MARKER)
    lines.append("## 9. Danh gia objective tren tap test (MCD, F0 RMSE, DTW)")
    lines.append("")
    lines.append("Nguon so lieu:")
    lines.append(f"- {summary_path.as_posix()}")
    lines.append("")
    lines.append("Cau hinh metric:")
    sample_cfg = p3 or p2 or p1
    lines.append(f"- sample_rate: {sample_cfg.get('sample_rate', 'N/A')}")
    lines.append(f"- n_mfcc: {sample_cfg.get('n_mfcc', 'N/A')} (drop_c0={sample_cfg.get('drop_c0', 'N/A')})")
    lines.append(f"- n_fft/hop_length: {sample_cfg.get('n_fft', 'N/A')}/{sample_cfg.get('hop_length', 'N/A')}")
    lines.append(f"- f0_min_hz/f0_max_hz: {sample_cfg.get('f0_min_hz', 'N/A')}/{sample_cfg.get('f0_max_hz', 'N/A')}")
    lines.append("")
    lines.append("| Phase | num_ok / num_items | MCD (dB) mean | DTW(MFCC) mean | F0 RMSE (Hz) mean |")
    lines.append("|---|---:|---:|---:|---:|")
    lines.append(
        "| Phase 1 best | "
        f"{p1.get('num_ok', 'N/A')} / {p1.get('num_items', 'N/A')} | "
        f"{fmt(p1.get('mcd_db_mean'))} | {fmt(p1.get('dtw_mfcc_mean'))} | {fmt(p1.get('f0_rmse_hz_mean'))} |"
    )
    lines.append(
        "| Phase 2 best | "
        f"{p2.get('num_ok', 'N/A')} / {p2.get('num_items', 'N/A')} | "
        f"{fmt(p2.get('mcd_db_mean'))} | {fmt(p2.get('dtw_mfcc_mean'))} | {fmt(p2.get('f0_rmse_hz_mean'))} |"
    )
    lines.append(
        "| Phase 3 best | "
        f"{p3.get('num_ok', 'N/A')} / {p3.get('num_items', 'N/A')} | "
        f"{fmt(p3.get('mcd_db_mean'))} | {fmt(p3.get('dtw_mfcc_mean'))} | {fmt(p3.get('f0_rmse_hz_mean'))} |"
    )
    lines.append("")
    lines.append("Nhan xet nhanh:")
    lines.append("- MCD cang thap thi pho nhac phan cang gan tham chieu.")
    lines.append("- F0 RMSE cang thap thi duong cao do cang on dinh va gan giong dich.")
    lines.append("- DTW(MFCC) giam cho thay do bien dang theo truc thoi gian giam.")
    lines.append(END_MARKER)
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inject test-set objective metrics into report")
    parser.add_argument(
        "--summary-json",
        default="runs/vieneu_tts/20260420_testset_eval_best3/all_phases_metrics_summary.json",
    )
    parser.add_argument(
        "--report-md",
        default="models/VieNeu-TTS/VIE_NEU_TTS_REPORT_FULL.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary_json)
    report_path = Path(args.report_md)

    if not summary_path.exists():
        raise FileNotFoundError(f"summary json not found: {summary_path}")
    if not report_path.exists():
        raise FileNotFoundError(f"report file not found: {report_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    section = build_section(summary, summary_path)

    text = report_path.read_text(encoding="utf-8")
    if START_MARKER in text and END_MARKER in text:
        start = text.index(START_MARKER)
        end = text.index(END_MARKER) + len(END_MARKER)
        new_text = text[:start] + section + text[end:]
    else:
        if not text.endswith("\n"):
            text += "\n"
        new_text = text + "\n" + section

    report_path.write_text(new_text, encoding="utf-8")
    print(f"report_updated={report_path}")
    print(f"summary_used={summary_path}")


if __name__ == "__main__":
    main()
