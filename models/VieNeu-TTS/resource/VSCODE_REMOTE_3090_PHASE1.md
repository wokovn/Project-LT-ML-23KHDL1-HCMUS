# VS Code Remote + Train Phase 1 (RTX 3090)

Tài liệu này mô tả quy trình kết nối máy thuê và chạy Phase 1 trong VS Code.

## 1) Chuẩn bị trên máy local

1. Cài VS Code.
2. Cài extension: Remote - SSH (Microsoft).
3. Tạo SSH key nếu chưa có:

```bash
ssh-keygen -t ed25519 -C "vieneu-3090"
```

4. Add public key lên dịch vụ cho thuê máy GPU.

## 2) Kết nối máy thuê bằng VS Code

1. Mở Command Palette: `Ctrl+Shift+P`.
2. Chạy `Remote-SSH: Add New SSH Host`.
3. Nhập host theo form:

```bash
ssh <username>@<rental_ip> -p <port>
```

4. Chạy `Remote-SSH: Connect to Host` và chọn host vừa tạo.
5. Khi kết nối xong, mở folder dự án trên remote machine.

## 3) Setup môi trường trên máy thuê

Trong terminal của VS Code (đang ở remote):

```bash
cd <path-to>/Project-LT-ML-23KHDL1-HCMUS
chmod +x models/VieNeu-TTS/templates/scripts/setup_rental_3090.sh
bash models/VieNeu-TTS/templates/scripts/setup_rental_3090.sh
source .venv/bin/activate
```

Với máy CUDA 12.4, nên đặt trước:

```bash
export TORCH_CUDA_TAG=cu124
bash models/VieNeu-TTS/templates/scripts/setup_rental_3090.sh
```

Nếu đổi sang máy CUDA 12.2 thì đổi lại `TORCH_CUDA_TAG=cu121`.

## 4) Chuẩn bị dữ liệu và model

1. Đảm bảo dữ liệu đã nằm trên remote machine (ví dụ: `data/xtts_stage2_24k_mono`) và `data_root` trong config trỏ đúng đường dẫn đó.
2. Đảm bảo model đã được tải vào `models/pretrained/VieNeu-TTS`.
3. Dùng config máy thuê: `models/VieNeu-TTS/templates/train_config_3phase_rtx3090.yaml` (đã set `dataloader_num_workers: 8`).

Gợi ý kiểm tra nhanh:

```bash
python - << 'PY'
import os
print('rental config exists:', os.path.exists('models/VieNeu-TTS/templates/train_config_3phase_rtx3090.yaml'))
print('model dir exists:', os.path.exists('models/pretrained/VieNeu-TTS'))
PY
```

## 5) Chạy Phase 1

Trước khi chạy, có thể dùng file env mẫu để giảm gõ lệnh tay:

```bash
cp models/VieNeu-TTS/templates/rental_3090.env.example models/VieNeu-TTS/templates/rental_3090.env
# sửa TRAIN_SCRIPT và data_root trong config nếu cần
source models/VieNeu-TTS/templates/rental_3090.env
```

### Cách A: chạy bằng tmux (khuyến nghị)

```bash
source .venv/bin/activate
chmod +x models/VieNeu-TTS/templates/scripts/run_phase1_3090_tmux.sh

TRAIN_SCRIPT=<PATH_TO_REAL_TRAIN_SCRIPT> \
CONFIG=models/VieNeu-TTS/templates/train_config_3phase_rtx3090.yaml \
bash models/VieNeu-TTS/templates/scripts/run_phase1_3090_tmux.sh

# theo dõi
TMUX_SESSION=vieneu_phase1
tmux attach -t ${TMUX_SESSION}
```

Detach tmux: `Ctrl+B`, sau đó `D`.

### Cách B: chạy trực tiếp trong terminal VS Code

```bash
source .venv/bin/activate
TRAIN_SCRIPT=<PATH_TO_REAL_TRAIN_SCRIPT> \
CONFIG=models/VieNeu-TTS/templates/train_config_3phase_rtx3090.yaml \
bash models/VieNeu-TTS/templates/scripts/run_phase1_warmup.sh
```

## 6) Smoke-first trước khi full run

Khuyến nghị chạy smoke train ngắn qua `EXTRA_ARGS` (tùy theo flag train script thực tế), ví dụ:

```bash
source .venv/bin/activate
TRAIN_SCRIPT=<PATH_TO_REAL_TRAIN_SCRIPT> \
CONFIG=models/VieNeu-TTS/templates/train_config_3phase_rtx3090.yaml \
EXTRA_ARGS="--max-steps 100 --max-epoch 1" \
bash models/VieNeu-TTS/templates/scripts/run_phase1_warmup.sh
```

Nếu smoke ổn định mới chạy full.

## 7) Theo dõi trong phiên thuê 24 giờ

Lặp chu kỳ kiểm tra:

```bash
nvidia-smi
df -h
```

Artifact chính sau Phase 1:

- `runs/vieneu_tts/<RUN_TAG>/phase1/checkpoints`
- `runs/vieneu_tts/<RUN_TAG>/phase1/logs`
- `runs/vieneu_tts/<RUN_TAG>/phase1/samples`
- `runs/vieneu_tts/<RUN_TAG>/phase1/metrics`
- `runs/vieneu_tts/<RUN_TAG>/phase1/handoff_phase2`

## 8) Handoff sang Phase 2

Sau khi chọn checkpoint tốt nhất từ Phase 1:

```bash
source .venv/bin/activate
PHASE1_CKPT=<PATH_TO_BEST_PHASE1_CKPT> \
TRAIN_SCRIPT=<PATH_TO_REAL_TRAIN_SCRIPT> \
bash models/VieNeu-TTS/templates/scripts/run_phase2_full_finetune.sh
```

## 9) Lưu ý quan trọng

- `TRAIN_SCRIPT` bắt buộc là entrypoint train thật của bạn trong repo.
- Không dùng Python 3.13 cho stack huấn luyện TTS; ưu tiên Python 3.11.
- Nếu thuê máy Linux nhưng data nằm ở ổ cục bộ Windows, cần copy/sync dữ liệu lên remote trước khi train.
