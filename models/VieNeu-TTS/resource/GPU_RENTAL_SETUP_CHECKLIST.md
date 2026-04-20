# Checklist Thiết Lập Máy GPU Thuê - Fine-tune VieNeu-TTS

Checklist này được viết cho bài toán fine-tune một hướng duy nhất: VieNeu-TTS.

## 0) Nguồn cố định của bài toán

- Dataset: https://www.kaggle.com/datasets/nhtlnguyn1106/xttsv2-finetuning-data-20260417
- Model: https://huggingface.co/pnnbao-ump/VieNeu-TTS
- Dataset trên Kaggle đang ở mức ~7.81 GB (xem Data Explorer).

## 1) Cấu hình máy thuê mục tiêu (phiên bản đang dùng)

- GPU: 1x RTX 3090 (24 GB VRAM)
- CPU: AMD Ryzen 9 5900XT (16/32 cores)
- RAM: 64.19 GB
- Disk: MSI M461 2TB (1704.1527 GB trống)
- Network: 183.36/461.18 Mbps
- Disk speed: 1745.04 MB/s
- CUDA: 12.4
- Rental ID: 81777

Nhận xét: Cấu hình này phù hợp cho chạy Phase 1/2/3. Dung lượng đĩa hiện tại thoải mái cho nhiều run thử.

## 2) Ước lượng dung lượng đĩa cần thuê (dataset ~8 GB)

### Ước lượng theo thành phần

- Dataset zip/ban đầu: 8-10 GB
- Dữ liệu sau giải nén + bản preprocess (resample/trim): 20-35 GB
- Checkpoints (top-k + last, có optimizer state): 40-90 GB
- Môi trường Python + pip cache + HuggingFace cache: 15-30 GB
- Logs, audio mẫu mỗi epoch, kết quả đánh giá: 5-15 GB

Tổng thực tế thường rơi vào khoảng 88-180 GB.

### Khuyến nghị gói dung lượng

- Tối thiểu có thể chạy: 120 GB (rất sát, dễ đầy ổ)
- Mức an toàn nên thuê: 200 GB trở lên
- Mức rất thoải mái cho nhiều lần thử: 300 GB trở lên

Với máy hiện tại còn ~1704 GB trống: đủ rộng rãi, không cần nâng cấp thêm disk.

## 3) Hệ điều hành và Python

- OS khuyến nghị: Ubuntu 22.04 LTS
- Python khuyến nghị: 3.10 hoặc 3.11
- Không dùng Python 3.13 cho stack TTS để tránh lỗi cài đặt gói

## 4) Lệnh khởi tạo nhanh trên máy thuê (Linux)

```bash
sudo apt update
sudo apt install -y git git-lfs ffmpeg sox libsndfile1 build-essential tmux htop unzip wget curl

git clone <YOUR_REPO_URL>
cd Project-LT-ML-23KHDL1-HCMUS
chmod +x models/VieNeu-TTS/templates/scripts/setup_rental_3090.sh
bash models/VieNeu-TTS/templates/scripts/setup_rental_3090.sh
```

Nếu chưa có python3.10:

```bash
sudo apt install -y python3.10 python3.10-venv
```

## 5) Cài PyTorch + thư viện huấn luyện

Đã được gom trong script setup:

- `models/VieNeu-TTS/templates/scripts/setup_rental_3090.sh`

Script sẽ:

1. Tạo venv (`.venv`) bằng Python 3.11.
2. Cài torch/torchaudio theo `TORCH_CUDA_TAG`.
3. Cài toàn bộ dependencies train từ `requirements-train.txt`.
4. In ra sanity check torch/cuda/gpu.

Máy CUDA 12.4 hiện tại nên dùng:

```bash
export TORCH_CUDA_TAG=cu124
bash models/VieNeu-TTS/templates/scripts/setup_rental_3090.sh
```

Nếu sau này đổi sang máy CUDA 12.2 thì chuyển về:

```bash
export TORCH_CUDA_TAG=cu121
bash models/VieNeu-TTS/templates/scripts/setup_rental_3090.sh
```

## 6) Config nên dùng trên máy thuê

- `models/VieNeu-TTS/templates/train_config_3phase_rtx3090.yaml`

Lưu ý:

1. Chỉnh `paths.data_root` theo đường dẫn dữ liệu đã copy lên máy remote.
2. Giữ `precision: fp16` và `dataloader_num_workers: 8` cho profile 3090 + CPU 16/32 cores.
3. Không đổi seed giữa các lần so sánh checkpoint nếu cần tái lập.

## 7) Tải dataset và model theo link có sẵn

### 7.1 Dataset từ Kaggle

```bash
mkdir -p data/raw data/xtts
kaggle datasets download -d nhtlnguyn1106/xttsv2-finetuning-data-20260417 -p data/raw --unzip
```

### 7.2 Model từ Hugging Face

```bash
python -m pip install -U huggingface_hub[hf_transfer]
huggingface-cli download pnnbao-ump/VieNeu-TTS --local-dir models/pretrained/VieNeu-TTS
```

## 8) Sanity check trước khi train

```bash
python - << 'PY'
import sys, torch
print('python:', sys.version)
print('torch:', torch.__version__)
print('cuda_available:', torch.cuda.is_available())
print('gpu_count:', torch.cuda.device_count())
if torch.cuda.is_available():
    print('gpu_name:', torch.cuda.get_device_name(0))
PY

nvidia-smi
df -h
```

## 9) Checklist dữ liệu trước khi huấn luyện

- Chốt sample rate duy nhất theo config train (khuyến nghị 24000 Hz), mono.
- Xác nhận file split cố định: train_wav.csv, eval.csv, test_wav.csv.
- Không reshuffle split giữa các lần chạy.
- Kiểm tra trùng lặp và leakage (nếu có nhiều speaker thì ưu tiên tách theo speaker).
- Chuẩn hóa transcript (số, viết tắt, dấu câu) nhất quán.

## 10) Runtime gợi ý cho RTX 3090 24 GB

- Mixed precision: fp16
- Gradient accumulation: 2-8
- Dataloader workers: 8 (máy 16/32 cores)
- Save top-k checkpoints: k=3
- Lưu optimizer state để chuyển phase 2 -> phase 3 mượt hơn
- Dùng early stopping theo validation loss

Config template hiện tại đã được chỉnh để phù hợp profile này (`dataloader_num_workers: 8`).

## 11) Chạy train an toàn bằng tmux

```bash
source .venv/bin/activate
cp models/VieNeu-TTS/templates/rental_3090.env.example models/VieNeu-TTS/templates/rental_3090.env
# sửa TRAIN_SCRIPT trong file env theo entrypoint thực tế của bạn
source models/VieNeu-TTS/templates/rental_3090.env
chmod +x models/VieNeu-TTS/templates/scripts/run_phase1_3090_tmux.sh

bash models/VieNeu-TTS/templates/scripts/run_phase1_3090_tmux.sh

# attach session
tmux attach -t vieneu_phase1
# detach: Ctrl+B rồi D
```

Script `run_phase1_3090_tmux.sh` sẽ gọi `run_phase1_warmup.sh` và tự log ra file để theo dõi.

## 11.1) Chạy trực tiếp không qua tmux (khi cần debug)

```bash
source .venv/bin/activate
TRAIN_SCRIPT=<PATH_TO_REAL_TRAIN_SCRIPT> \
bash models/VieNeu-TTS/templates/scripts/run_phase1_warmup.sh
```

## 11.2) Theo dõi tiến độ trong giới hạn thuê 24 giờ

- Ưu tiên chạy smoke train ngắn trước, sau đó mới full Phase 1.
- Kiểm tra nhanh mỗi 30-60 phút:
    - `nvidia-smi`
    - dung lượng ổ đĩa `df -h`
    - log train trong `runs/vieneu_tts/<RUN_TAG>/phase1/`

Nếu gần hết giờ thuê, ưu tiên đảm bảo checkpoint + logs + samples đã đồng bộ về nơi lưu bền vững.

## 11.3) Chạy qua VS Code Remote SSH

Xem chi tiết tại:

- `models/VieNeu-TTS/resource/VSCODE_REMOTE_3090_PHASE1.md`

## 12) Chính sách log và lưu trữ

Cần lưu đầy đủ mỗi run:

- train_loss/val_loss theo epoch
- metric đánh giá (MCD, WER/CER, MOS)
- audio mẫu từ tập câu cố định mỗi epoch
- top-k checkpoint + last checkpoint
- file config run + thông tin môi trường (python/cuda/torch/TTS)

## 13) Lỗi thường gặp

- pip install tts lỗi: thường do sai Python version hoặc sai tên gói. Dùng Python 3.10/3.11 và cài TTS.
- CUDA OOM: giảm batch, tăng grad accumulation, giảm độ dài audio.
- Tốc độ data loader chậm: đặt dữ liệu trên SSD, tinh chỉnh num_workers.
- Audio rè/robot: kiểm tra lại sample rate, trim silence, transcript.

## 14) File cần mang theo khi chuyển máy

- models/VieNeu-TTS/resource/Workflow.md
- models/VieNeu-TTS/resource/Báo cáo.md
- models/VieNeu-TTS/resource/link.txt
- training config đang dùng
- metadata checkpoint tốt nhất (epoch, val loss, metric)
