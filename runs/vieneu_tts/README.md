# VieNeu-TTS Pipeline Run Directory

Thu muc nay chua artifact cho tung lan chay train theo workflow 3 phase.

## Cau truc de xuat moi run

- `<RUN_TAG>/phase1/`
- `<RUN_TAG>/phase2/`
- `<RUN_TAG>/phase3/`

Trong `phase1/` script warmup se tu dong tao:

- `checkpoints/`
- `logs/`
- `samples/`
- `metrics/`
- `handoff_phase2/`
  - `phase1_config_snapshot.yaml`
  - `phase2_next_steps.md`

## Du lieu dau vao cho train

Mac dinh config hien tai tro vao du lieu da qua chuan hoa giai doan 2:

- `D:/HCMUS/data_project_LT/xtts_stage2_24k_mono/train_wav.csv`
- `D:/HCMUS/data_project_LT/xtts_stage2_24k_mono/eval.csv`
- `D:/HCMUS/data_project_LT/xtts_stage2_24k_mono/test_wav.csv`

## Sau khi xong Phase 1 can lam gi de vao Phase 2

1. Chon `BEST_PHASE1_CKPT` dua tren val_loss va nghe audio samples.
2. Chot nhan xet loi phat am/ngat nghi tu bo mau co dinh.
3. Ghi lai thay doi hyperparameter can dieu chinh cho phase2.
4. Chay phase2 voi checkpoint da chon:

```bash
PHASE1_CKPT=<PATH_TO_BEST_PHASE1_CKPT> \
bash models/VieNeu-TTS/templates/scripts/run_phase2_full_finetune.sh
```
