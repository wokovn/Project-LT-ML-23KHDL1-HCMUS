# Hướng Dẫn Smoke Test (cho Giai đoạn 2 + kiểm tra train nhanh)

## Vì sao Giai đoạn 2 vẫn cần thiết dù dữ liệu đã được chuẩn hóa

Chuẩn hóa dữ liệu ở mức tổng quát là chưa đủ. VieNeu-TTS vẫn cần căn chỉnh theo cấu hình riêng của mô hình để dữ liệu khớp tuyệt đối với pipeline train.

Ví dụ:
- Sample rate phải khớp cấu hình (ví dụ 24000 Hz).
- Số kênh phải là mono.
- Mức trim silence cần đủ chặt để tránh ngắt nghỉ bất thường.
- Quy tắc chuẩn hóa văn bản phải khớp với tokenizer khi train.
- Giới hạn độ dài và bộ lọc cần phù hợp với runtime của mô hình.

Vì vậy, Giai đoạn 2 không phải "làm lại cho có" mà là lớp tương thích giữa dataset và đúng cấu hình mô hình đang dùng.

## Bước A - Chạy kiểm tra nhanh dataset alignment theo model

```bash
python models/VieNeu-TTS/templates/scripts/smoke_test_dataset_alignment.py \
  --data-root data/xtts \
  --csv data/xtts/train_wav.csv \
  --csv data/xtts/eval.csv \
  --expected-sr 24000 \
  --expected-channels 1 \
  --max-samples 256 \
  --fail-on-warning
```

Nếu lệnh này lỗi, cần xử lý vấn đề dữ liệu trước khi train.

## Bước B - Tạo tập con nhỏ để smoke test (deterministic)

```bash
python models/VieNeu-TTS/templates/scripts/create_smoke_subset.py \
  --train-csv data/xtts/train_wav.csv \
  --eval-csv data/xtts/eval.csv \
  --output-dir data/xtts/smoke \
  --train-n 64 \
  --eval-n 16 \
  --seed 20260419
```

Đầu ra:
- data/xtts/smoke/train_smoke.csv
- data/xtts/smoke/eval_smoke.csv

## Bước C - Chạy smoke train nhanh cho Phase 1

Sử dụng script train của bạn và trỏ vào các CSV của smoke subset.

Ví dụ mẫu:

```bash
PYTHON_BIN=python \
TRAIN_SCRIPT=train_xtts.py \
CONFIG=models/VieNeu-TTS/templates/train_config_3phase.yaml \
OUT_DIR=runs/vieneu_tts/smoke_phase1 \
EXTRA_ARGS="--train-csv data/xtts/smoke/train_smoke.csv --eval-csv data/xtts/smoke/eval_smoke.csv --max-steps 100 --epochs 1" \
./models/VieNeu-TTS/templates/scripts/run_phase1_warmup.sh
```

Nếu bạn dùng PowerShell, đặt biến môi trường rồi chạy script:

```powershell
$env:PYTHON_BIN = "python"
$env:TRAIN_SCRIPT = "train_xtts.py"
$env:CONFIG = "models/VieNeu-TTS/templates/train_config_3phase.yaml"
$env:OUT_DIR = "runs/vieneu_tts/smoke_phase1"
$env:EXTRA_ARGS = "--train-csv data/xtts/smoke/train_smoke.csv --eval-csv data/xtts/smoke/eval_smoke.csv --max-steps 100 --epochs 1"
bash models/VieNeu-TTS/templates/scripts/run_phase1_warmup.sh
```

## Bước D - Tiêu chí đạt smoke test

- Train khởi chạy và chạy được, không lỗi shape mismatch.
- Có log train loss và val loss.
- Lưu được ít nhất một checkpoint.
- Lưu được optimizer state.
- Sinh được ít nhất một audio sample.
- Audio nghe được (không im lặng, không nhiễu nặng, không cắt cụt nghiêm trọng).

Nếu tất cả tiêu chí đều đạt, chuyển sang chạy full Phase 1 với train/eval đầy đủ.
