import os, glob, json
import numpy as np
import torch
import librosa
import warnings
warnings.filterwarnings('ignore')

from config.global_config import GlobalConfig
from audio.pitch import yin
from metrics.FFE import f0_frame_error
from metrics.DTW import batch_dynamic_time_warping
from metrics.MCD import batch_mel_cepstral_distortion

config = GlobalConfig()

gt_dir = os.path.join('data','gt')
pred_dir = os.path.join('data','pred')
gt_files = sorted([os.path.basename(p) for p in glob.glob(os.path.join(gt_dir,'*.wav'))])
pred_files = sorted([os.path.basename(p) for p in glob.glob(os.path.join(pred_dir,'*.wav'))])
if gt_files != pred_files:
    raise RuntimeError('Mismatch filenames between gt/pred')

ffe_vals, dtw_vals, mcd_vals = [], [], []

for fname in gt_files:
    x_gt, _ = librosa.load(os.path.join(gt_dir, fname))
    x_pred, _ = librosa.load(os.path.join(pred_dir, fname))

    p_gt = yin(x_gt, config)
    p_pred = yin(x_pred, config)

    ffe = f0_frame_error(np.array(p_gt['times']), np.array(p_gt['pitches']), np.array(p_pred['times']), np.array(p_pred['pitches']))
    if np.isfinite(ffe):
        ffe_vals.append(float(ffe))

    t_gt = torch.tensor(p_gt['pitches'], dtype=torch.float32).unsqueeze(1)
    t_pred = torch.tensor(p_pred['pitches'], dtype=torch.float32).unsqueeze(1)
    dtw = batch_dynamic_time_warping([t_gt], [t_pred], config.dist_fn, config.norm_align_type)['norm_align_costs'][0]
    if np.isfinite(dtw):
        dtw_vals.append(float(dtw))

    mcd = batch_mel_cepstral_distortion([torch.tensor(x_gt, dtype=torch.float32)], [torch.tensor(x_pred, dtype=torch.float32)], config)[0]
    if np.isfinite(mcd):
        mcd_vals.append(float(mcd))

def stats(values):
    arr = np.array(values, dtype=np.float64)
    return {
        'count': int(arr.size),
        'mean': float(np.mean(arr)) if arr.size else None,
        'std': float(np.std(arr)) if arr.size else None,
        'min': float(np.min(arr)) if arr.size else None,
        'max': float(np.max(arr)) if arr.size else None,
    }

print(json.dumps({
    'pairs': len(gt_files),
    'FFE': stats(ffe_vals),
    'DTW': stats(dtw_vals),
    'MCD': stats(mcd_vals)
}, indent=2))
