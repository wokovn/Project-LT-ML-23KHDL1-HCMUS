# Checklist Thiết Lập Máy GPU Thuê - Fine-tune VieNeu-TTS

Checklist này được viết cho bài toán fine-tune một hướng duy nhất: VieNeu-TTS.

## 0) Nguồn cố định của bài toán

- Dataset: https://www.kaggle.com/datasets/nhtlnguyn1106/xttsv2-finetuning-data-20260417
- Model: https://huggingface.co/pnnbao-ump/VieNeu-TTS
- Dataset trên Kaggle đang ở mức ~7.81 GB (xem Data Explorer).

## 1) Cấu hình máy thuê mục tiêu (theo Workflow)

- GPU: 1x RTX 3090 (24 GB VRAM)
- CPU: Xeon E5-2630 v4 (20 cores)
- RAM: 125.88 GB
- Disk: 591 GB
- CUDA: 12.6

Nhận xét: Cấu hình trên đủ và thoải mái cho VieNeu-TTS fine-tune theo 3 phase.

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

Với máy 591 GB trong workflow: đủ rộng rãi, không cần nâng cấp thêm disk.

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
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Nếu chưa có python3.10:

```bash
sudo apt install -y python3.10 python3.10-venv
```

## 5) Cài PyTorch cho GPU

CUDA driver 12.6 có thể chạy wheel cu121/cu124.

```bash
# Lựa chọn phù hợp và giữ cố định cho cả project
pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
```

## 6) Cài thư viện huấn luyện

```bash
pip install pandas numpy scipy librosa soundfile matplotlib pyyaml tqdm
pip install datasets evaluate jiwer tensorboard wandb kaggle huggingface_hub

# Lưu ý: dùng gói TTS (chữ hoa), không dùng tts
pip install TTS==0.22.0
```

Nếu TTS 0.22.0 lỗi, dùng fallback:

```bash
pip install git+https://github.com/coqui-ai/TTS.git
```

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
- Save top-k checkpoints: k=3
- Lưu optimizer state để chuyển phase 2 -> phase 3 mượt hơn
- Dùng early stopping theo validation loss

## 11) Chạy train an toàn bằng tmux

```bash
tmux new -s tts_train
# chạy lệnh train
# bấm Ctrl+B rồi bấm D để detach
```

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
