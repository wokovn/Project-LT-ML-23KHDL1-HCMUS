import argparse
import concurrent.futures
import csv
import math
import os

os.environ.pop("MPLBACKEND", None)
import matplotlib
matplotlib.use("Agg")

from collections import defaultdict
from pathlib import Path
from typing import List, Tuple

import librosa
import numpy as np
import soundfile as sf
from scipy.fft import dct
from TTS.api import TTS
from pymcd.mcd import Calculate_MCD

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Vietnamese TTS with MCD, FFE, and DTW.")
    parser.add_argument("--model-path", required=True, help="Path to checkpoint .pth.")
    parser.add_argument("--config-path", required=True, help="Path to config.json.")
    parser.add_argument("--pairs-csv", required=True, help="CSV with columns: text|ref_wav|speaker_name.")
    parser.add_argument("--output-dir", required=True, help="Directory to save synthesized wavs and metrics.")
    parser.add_argument("--gpu", action="store_true", help="Use GPU for TTS when available.")
    parser.add_argument("--max-samples", type=int, default=0, help="If > 0, evaluate only first N rows.")
    return parser.parse_args()

def load_pairs(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="|")
        required = {"text", "ref_wav", "speaker_name"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("pairs-csv must contain columns: text|ref_wav|speaker_name")
        for row in reader:
            rows.append(
                {
                    "text": (row.get("text") or "").strip(),
                    "ref_wav": (row.get("ref_wav") or "").strip(),
                    "speaker_name": (row.get("speaker_name") or "").strip(),
                }
            )
    return [r for r in rows if r["text"] and r["ref_wav"]]

def compute_acoustic_metrics(ref_wav: str, syn_wav: str, sr: int = 22050) -> Tuple[float, float]:
    y_ref, _ = librosa.load(ref_wav, sr=sr)
    y_syn, _ = librosa.load(syn_wav, sr=sr)
    
    if y_ref.size == 0 or y_syn.size == 0:
        return float('nan'), float('nan')

    # Normalize audio amplitudes to [-1.0, 1.0] to remove volume-based penalty
    y_ref = y_ref / max(0.001, np.max(np.abs(y_ref)))
    y_syn = y_syn / max(0.001, np.max(np.abs(y_syn)))
    
    # 2. Mel-Spectrogram for DTW Structural Distance and F0 alignment
    # Standard settings for speech: 80 mels, 1024 n_fft, 256 hop
    S_ref = librosa.feature.melspectrogram(y=y_ref, sr=sr, n_fft=1024, hop_length=256, n_mels=80)
    S_syn = librosa.feature.melspectrogram(y=y_syn, sr=sr, n_fft=1024, hop_length=256, n_mels=80)
    
    # Use ref=1.0 absolute scale to compare structural differences consistently
    log_S_ref = librosa.power_to_db(S_ref, ref=1.0)
    log_S_syn = librosa.power_to_db(S_syn, ref=1.0)
    
    # Mel-DTW Cost
    dist_mel, wp_mel = librosa.sequence.dtw(X=log_S_ref, Y=log_S_syn, metric="euclidean")
    dtw_distance = float(dist_mel[-1, -1] / (len(wp_mel) * 80.0))
    
    f0_ref, _, _ = librosa.pyin(y_ref, sr=sr, fmin=65, fmax=600, hop_length=256)
    f0_syn, _, _ = librosa.pyin(y_syn, sr=sr, fmin=65, fmax=600, hop_length=256)
    
    # wp_mel returns indices [[i, j], ...] but in reverse order.
    # We must reverse the array to align from Left to Right.
    wp_mel = wp_mel[::-1, :]  
    
    # Extract aligned F0 frames based on DTW path
    aligned_f0_ref = f0_ref[wp_mel[:, 0]]
    aligned_f0_syn = f0_syn[wp_mel[:, 1]]
    
    # Compute FFE (F0 Frame Error) = VDE (Voicing Decision Error) + GPE (Gross Pitch Error)
    v_ref = ~np.isnan(aligned_f0_ref)
    v_syn = ~np.isnan(aligned_f0_syn)
    
    total_frames = len(aligned_f0_ref)
    if total_frames > 0:
        # VDE: Voicing state mismatch
        vde_frames = np.sum(v_ref != v_syn)
        # GPE: Both voiced, but F0 difference > 20%
        both_voiced = v_ref & v_syn
        gpe_frames = np.sum(both_voiced & (np.abs(aligned_f0_ref - aligned_f0_syn) > 0.2 * aligned_f0_ref))
        
        ffe_rate = float((vde_frames + gpe_frames) / total_frames)
    else:
        ffe_rate = float('nan')
        
    return ffe_rate, dtw_distance

def evaluate_single_pair(ref_wav: str, syn_path: str, sr: int) -> dict:
    from pymcd.mcd import Calculate_MCD
    mcd_toolbox = Calculate_MCD(MCD_mode="dtw_sl")
    mcd = float(mcd_toolbox.calculate_mcd(ref_wav, syn_path))
    ffe_rate, dtw = compute_acoustic_metrics(ref_wav, syn_path, sr=sr)
    return {"mcd": mcd, "ffe_rate": ffe_rate, "dtw": dtw}

def main() -> None:
    args = parse_args()
    model_path = Path(args.model_path).resolve()
    config_path = Path(args.config_path).resolve()
    pairs_csv = Path(args.pairs_csv).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    synth_dir = output_dir / "synth_wavs"
    synth_dir.mkdir(parents=True, exist_ok=True)

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    if not pairs_csv.exists():
        raise FileNotFoundError(f"pairs-csv not found: {pairs_csv}")

    rows = load_pairs(pairs_csv)
    if args.max_samples > 0:
        rows = rows[: args.max_samples]
    if not rows:
        raise ValueError("No valid rows to evaluate.")

    tts = TTS(model_path=str(model_path), config_path=str(config_path), gpu=args.gpu)
    sample_rate = tts.synthesizer.output_sample_rate

    print(f"Phase 1: Synthesizing {len(rows)} samples sequentially...")
    synth_jobs = []
    for idx, row in enumerate(rows):
        ref_wav = Path(row["ref_wav"]).expanduser().resolve()
        if not ref_wav.exists():
            print(f"  [Skipped] Reference not found: {ref_wav}")
            continue

        wav = tts.synthesizer.tts(text=row["text"], speaker_name=row["speaker_name"], language_name=None)
        syn_path = synth_dir / f"{idx:04d}_{row['speaker_name']}.wav"
        sf.write(str(syn_path), np.asarray(wav, dtype=np.float32), sample_rate)
        synth_jobs.append((idx, row, str(ref_wav), str(syn_path)))
        print(f"  [Gen {idx+1}/{len(rows)}] Saved {syn_path.name}")

    print(f"\nPhase 2: Evaluating metrics using {os.cpu_count() or 4} CPU cores in parallel...")
    details = []
    scores_mcd, scores_ffe, scores_dtw = [], [], []

    # Bypass GIL limitations with ProcessPoolExecutor to max out all available CPUs
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_idx = {}
        for item in synth_jobs:
            idx, row, ref_wav, syn_path = item
            future = executor.submit(evaluate_single_pair, ref_wav, syn_path, sample_rate)
            future_to_idx[future] = item
            
        completed = 0
        for future in concurrent.futures.as_completed(future_to_idx):
            idx, row, ref_wav, syn_path = future_to_idx[future]
            try:
                res = future.result()
                mcd, ffe_rate, dtw = res["mcd"], res["ffe_rate"], res["dtw"]
                if not math.isnan(mcd): scores_mcd.append(mcd)
                if not math.isnan(ffe_rate): scores_ffe.append(ffe_rate)
                if not math.isnan(dtw): scores_dtw.append(dtw)
                
                details.append({
                    "idx": idx,
                    "speaker_name": row["speaker_name"],
                    "ref_wav": ref_wav,
                    "syn_wav": syn_path,
                    "mcd_db": mcd,
                    "ffe_rate": ffe_rate,
                    "dtw_cost": dtw,
                })
                completed += 1
                print(f"  [Eval {completed}/{len(synth_jobs)}] @{row['speaker_name']} | MCD: {mcd:.2f} | FFE: {ffe_rate:.4f} | DTW: {dtw:.2f}")
            except Exception as exc:
                print(f"  [Error] Eval failed for {syn_path}: {exc}")

    # --- Calculate overall means ---
    mean_mcd = float(np.mean(scores_mcd)) if scores_mcd else float("nan")
    mean_ffe = float(np.mean(scores_ffe)) if scores_ffe else float("nan")
    mean_dtw = float(np.mean(scores_dtw)) if scores_dtw else float("nan")

    # --- Calculate per-speaker means ---
    speaker_stats = defaultdict(lambda: {"mcd": [], "ffe": [], "dtw": []})
    for d in details:
        if not math.isnan(d["mcd_db"]): speaker_stats[d["speaker_name"]]["mcd"].append(d["mcd_db"])
        if not math.isnan(d["ffe_rate"]): speaker_stats[d["speaker_name"]]["ffe"].append(d["ffe_rate"])
        if not math.isnan(d["dtw_cost"]): speaker_stats[d["speaker_name"]]["dtw"].append(d["dtw_cost"])

    details_csv = output_dir / "acoustic_eval_details.csv"
    with details_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["idx", "speaker_name", "ref_wav", "syn_wav", "mcd_db", "ffe_rate", "dtw_cost"]
        )
        writer.writeheader()
        writer.writerows(details)

    summary_csv = output_dir / "acoustic_eval_summary.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["speaker_name", "num_samples", "mean_mcd_db", "mean_ffe_rate", "mean_dtw_cost"])
        writer.writeheader()
        
        # Write Overall
        writer.writerow({
            "speaker_name": "ALL",
            "num_samples": len(details), 
            "mean_mcd_db": mean_mcd, 
            "mean_ffe_rate": mean_ffe, 
            "mean_dtw_cost": mean_dtw
        })
        
        # Write Per Speaker
        for spk, stats in speaker_stats.items():
            s_mcd = float(np.mean(stats["mcd"])) if stats["mcd"] else float("nan")
            s_ffe = float(np.mean(stats["ffe"])) if stats["ffe"] else float("nan")
            s_dtw = float(np.mean(stats["dtw"])) if stats["dtw"] else float("nan")
            writer.writerow({
                "speaker_name": spk,
                "num_samples": len(stats["mcd"]),
                "mean_mcd_db": s_mcd,
                "mean_ffe_rate": s_ffe,
                "mean_dtw_cost": s_dtw
            })

    print("-" * 50)
    print(f"EVALUATION COMPLETED {len(details)} Files) -> OVERALL AVERAGE:")
    print(f" [ALL] MCD: {mean_mcd:.4f} dB | FFE: {mean_ffe:.4f} | DTW: {mean_dtw:.4f}")
    print("-" * 50)
    print("PER-SPEAKER BREAKDOWN:")
    for spk, stats in speaker_stats.items():
        s_mcd = float(np.mean(stats["mcd"])) if stats["mcd"] else float("nan")
        s_ffe = float(np.mean(stats["ffe"])) if stats["ffe"] else float("nan")
        s_dtw = float(np.mean(stats["dtw"])) if stats["dtw"] else float("nan")
        print(f" [{spk}] (N={len(stats['mcd'])}) | MCD: {s_mcd:.4f} dB | FFE: {s_ffe:.4f} | DTW: {s_dtw:.4f}")
    print("-" * 50)
    print(f"Details saved to: {details_csv}")
    print(f"Summary saved to: {summary_csv}")

if __name__ == "__main__":
    main()
