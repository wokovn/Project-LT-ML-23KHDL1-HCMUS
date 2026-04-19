# GPU Rental Setup Checklist - VieNeu-TTS Fine-tuning

Checklist nay duoc viet cho bai toan fine-tune 1 huong duy nhat: VieNeu-TTS.

## 0) Nguon co dinh cua bai toan

- Dataset: https://www.kaggle.com/datasets/nhtlnguyn1106/xttsv2-finetuning-data-20260417
- Model: https://huggingface.co/pnnbao-ump/VieNeu-TTS
- Dataset tren Kaggle dang o muc ~7.81 GB (xem Data Explorer).

## 1) Cau hinh may thue muc tieu (theo Workflow)

- GPU: 1x RTX 3090 (24 GB VRAM)
- CPU: Xeon E5-2630 v4 (20 cores)
- RAM: 125.88 GB
- Disk: 591 GB
- CUDA: 12.6

Nhan xet: Cau hinh tren la du va thoai mai cho VieNeu-TTS fine-tune theo 3 phase.

## 2) Uoc luong dung luong dia can thue (dataset ~8 GB)

### Uoc luong theo thanh phan

- Dataset zip/ban dau: 8-10 GB
- Du lieu sau giai nen + ban preprocess (resample/trim): 20-35 GB
- Checkpoints (top-k + last, co optimizer state): 40-90 GB
- Moi truong Python + pip cache + HuggingFace cache: 15-30 GB
- Logs, audio mau moi epoch, ket qua danh gia: 5-15 GB

Tong thuc te thuong roi vao khoang 88-180 GB.

### Khuyen nghi goi dung luong

- Toi thieu co the chay: 120 GB (rat sat, de day o)
- Muc an toan nen thue: 200 GB tro len
- Muc rat thoai mai cho nhieu lan thu: 300 GB tro len

Voi may 591 GB trong workflow: du rong rai, khong can nang cap them disk.

## 3) He dieu hanh va Python

- OS khuyen nghi: Ubuntu 22.04 LTS
- Python khuyen nghi: 3.10 hoac 3.11
- Khong dung Python 3.13 cho stack TTS de tranh loi cai dat goi

## 4) Lenh khoi tao nhanh tren may thue (Linux)

```bash
sudo apt update
sudo apt install -y git git-lfs ffmpeg sox libsndfile1 build-essential tmux htop unzip wget curl

git clone <YOUR_REPO_URL>
cd Project-LT-ML-23KHDL1-HCMUS
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Neu chua co python3.10:

```bash
sudo apt install -y python3.10 python3.10-venv
```

## 5) Cai PyTorch cho GPU

CUDA driver 12.6 co the chay wheel cu121/cu124.

```bash
# Lua chon phu hop va giu co dinh cho ca project
pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
```

## 6) Cai thu vien huan luyen

```bash
pip install pandas numpy scipy librosa soundfile matplotlib pyyaml tqdm
pip install datasets evaluate jiwer tensorboard wandb kaggle huggingface_hub

# Luu y: dung goi TTS (chu hoa), khong dung tts
pip install TTS==0.22.0
```

Neu TTS 0.22.0 loi, dung fallback:

```bash
pip install git+https://github.com/coqui-ai/TTS.git
```

## 7) Tai dataset va model theo link co san

### 7.1 Dataset tu Kaggle

```bash
mkdir -p data/raw data/xtts
kaggle datasets download -d nhtlnguyn1106/xttsv2-finetuning-data-20260417 -p data/raw --unzip
```

### 7.2 Model tu Hugging Face

```bash
python -m pip install -U huggingface_hub[hf_transfer]
huggingface-cli download pnnbao-ump/VieNeu-TTS --local-dir models/pretrained/VieNeu-TTS
```

## 8) Sanity check truoc khi train

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

## 9) Checklist du lieu truoc khi huan luyen

- Chot sample rate duy nhat theo config train (khuyen nghi 24000 Hz), mono.
- Xac nhan file split co dinh: train_wav.csv, eval.csv, test_wav.csv.
- Khong reshuffle split giua cac lan chay.
- Kiem tra trung lap va leakage (neu co nhieu speaker thi uu tien tach theo speaker).
- Chuan hoa transcript (so, viet tat, dau cau) nhat quan.

## 10) Runtime goi y cho RTX 3090 24 GB

- Mixed precision: fp16
- Gradient accumulation: 2-8
- Save top-k checkpoints: k=3
- Luu optimizer state de chuyen phase 2 -> phase 3 muot hon
- Dung early stopping theo validation loss

## 11) Chay train an toan bang tmux

```bash
tmux new -s tts_train
# chay lenh train
# bam Ctrl+B roi bam D de detach
```

## 12) Chinh sach log va luu tru

Can luu day du moi run:

- train_loss/val_loss theo epoch
- metric danh gia (MCD, WER/CER, MOS)
- audio mau tu tap cau co dinh moi epoch
- top-k checkpoint + last checkpoint
- file config run + thong tin moi truong (python/cuda/torch/TTS)

## 13) Loi thuong gap

- pip install tts loi: thuong do sai Python version hoac sai ten goi. Dung Python 3.10/3.11 va cai TTS.
- CUDA OOM: giam batch, tang grad accumulation, giam do dai audio.
- Toc do data loader cham: dat du lieu tren SSD, tinh chinh num_workers.
- Audio re/robot: kiem tra lai sample rate, trim silence, transcript.

## 14) File can mang theo khi chuyen may

- models/VieNeu-TTS/resource/Workflow.md
- models/VieNeu-TTS/resource/Báo cáo.md
- models/VieNeu-TTS/resource/link.txt
- training config dang dung
- metadata checkpoint tot nhat (epoch, val loss, metric)
