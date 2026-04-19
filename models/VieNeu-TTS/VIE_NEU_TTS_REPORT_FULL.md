# BÁO CÁO HOÀN CHỈNH - FINE-TUNE VIE_NEU_TTS

## Trang bìa

- Tên đề tài: Fine-tune VieNeu-TTS cho bài toán Text-to-Speech tiếng Việt
- Nhóm/cá nhân thực hiện: [ĐIỀN THÔNG TIN]
- Môn học: [ĐIỀN THÔNG TIN]
- Giảng viên hướng dẫn: [ĐIỀN THÔNG TIN]
- Thời gian: [ĐIỀN THÔNG TIN]

## Mục lục

1. Giới thiệu bài toán
2. Tổng quan dữ liệu đầu vào
3. Lựa chọn mô hình và kiến trúc
4. Cấu hình huấn luyện
5. Kết quả thực nghiệm
6. Thảo luận và phân tích lỗi
7. Kết luận và hướng phát triển
8. Yêu cầu trình bày và trích dẫn
9. Phụ lục tracking kết quả

---

## 1. Giới thiệu bài toán

### 1.1 Bối cảnh
Bài toán Text-to-Speech (TTS) tiếng Việt có nhu cầu cao trong trợ lý ảo, tổng đài, trình đọc nội dung và hệ thống hỗ trợ người khiếm thị.

### 1.2 Phát biểu bài toán
Mục tiêu là fine-tune mô hình VieNeu-TTS để cải thiện chất lượng phát âm, nhịp điệu, độ tự nhiên và độ ổn định âm thanh trên tập dữ liệu mục tiêu.

### 1.3 Phạm vi
- Phạm vi cá nhân: chỉ tập trung một hướng duy nhất là VieNeu-TTS.
- Baseline nội bộ: checkpoint gốc (không fine-tune).
- Mô hình đánh giá chính: checkpoint fine-tune tốt nhất.

### 1.4 Đóng góp chính
- Thiết kế pipeline căn chỉnh dữ liệu theo cấu hình mô hình.
- Huấn luyện 3 phase (warmup, full finetune, refine).
- Đánh giá bằng metric định lượng và nghe thử chủ quan.

---

## 2. Tổng quan dữ liệu đầu vào

### 2.1 Nguồn dữ liệu và mô tả
- Dataset: XTTSv2 Finetuning Data 20260417 (Kaggle).
- Quy mô tham khảo: khoảng 7.81 GB, ~14.5k files.
- Cấu trúc file:
  - wavs/
  - metadata.csv
  - train_wav.csv
  - eval.csv
  - test_wav.csv

### 2.2 Chia tập dữ liệu
- Sử dụng split có sẵn train_wav.csv / eval.csv / test_wav.csv.
- Không reshuffle split giữa các lần chạy.
- Lý do: đảm bảo công bằng giữa các run và giảm data leakage.

### 2.3 Tiền xử lý dữ liệu (dataset alignment theo model)
Dữ liệu có thể đã được chuẩn hóa tổng quát, nhưng vẫn cần căn chỉnh theo cấu hình cụ thể của VieNeu-TTS:

1. Đồng bộ âm thanh:
- Sample rate: 24000 Hz.
- Số kênh: mono.

2. Trim silence:
- Cắt khoảng lặng ở đầu/cuối theo VAD.
- Mục tiêu: tránh ngắt nghỉ bất thường khi tổng hợp giọng.

3. Chuẩn hóa văn bản:
- Chuẩn hóa số, viết tắt, khoảng trắng, dấu câu.
- Đảm bảo phù hợp với tokenizer trong pipeline train.

4. Ràng buộc bổ sung:
- Giới hạn độ dài audio.
- Kiểm tra file hỏng, text rỗng, mismatch metadata.

### 2.4 Tác động kỳ vọng
- Giảm lỗi mismatch tensor.
- Tăng tốc độ hội tụ phase 1.
- Giảm lỗi nuốt chữ, lặp từ, robot voice.

---

## 3. Lựa chọn mô hình và kiến trúc

### 3.1 Mô hình được sử dụng
- VieNeu-TTS (XTTSv2) là mô hình duy nhất trong phạm vi báo cáo cá nhân.

### 3.2 Lý do lựa chọn
- Hỗ trợ tiếng Việt và voice cloning.
- Đã có checkpoint pretrain tốt cho fine-tune.
- Phù hợp bài toán với nguồn GPU hiện có.

### 3.3 Kiến trúc chi tiết
- Luồng tổng quát: Text + (optional reference audio) -> Acoustic/LM stack -> Vocoder -> waveform.
- Các thành phần cần mô tả trong bản nộp:
  - Số tham số mô hình (điền theo model card).
  - Kích thước input/output.
  - Các block được freeze/unfreeze theo phase.

### 3.4 Baseline so sánh
- Baseline nội bộ: checkpoint gốc.
- So sánh với checkpoint fine-tune tốt nhất.

---

## 4. Cấu hình huấn luyện

### 4.1 Hàm mất mát
- [ĐIỀN HÀM LOSS THỰC TẾ BẠN DÙNG]
- Lý do chọn: [ĐIỀN LÝ DO]

### 4.2 Tối ưu và scheduler
- Optimizer: [VD AdamW]
- Scheduler: [VD Cosine]
- Early stopping theo val_loss với patience: [ĐIỀN]

### 4.3 Chiến lược 3 phase

1. Phase 1 - Warmup
- Mục tiêu: ổn định huấn luyện và căn chỉnh phát âm.
- Freeze: DVAE, vocoder.
- Unfreeze: GPT, decoder.

2. Phase 2 - Full finetune
- Mục tiêu: học mạnh trên dữ liệu mục tiêu.
- Mở rộng unfreeze theo config.
- Epoch mặc định 8 là baseline; nếu val_loss còn giảm rõ ràng thì mở rộng 10-15.

3. Phase 3 - Refine
- Mục tiêu: hạ LR để làm mịn chất lượng âm thanh.

### 4.4 Cấu hình runtime và phần cứng
- GPU: RTX 3090 24GB.
- CPU: Xeon E5-2630 v4 (20 cores).
- RAM: 125.88 GB.
- Disk: 591 GB.
- CUDA: 12.6.

### 4.5 Tính tái lập
- Cố định seed.
- Lưu full config mỗi run.
- Lưu env manifest (python/cuda/torch/TTS/driver).

---

## 5. Kết quả thực nghiệm

### 5.1 Biểu đồ quá trình học
- Vẽ Train loss và Val loss theo epoch.
- Nhận xét:
  - Có hội tụ không?
  - Có dao động mạnh không?
  - Có dấu hiệu overfit sớm không?

### 5.2 Đánh giá tập kiểm tra
Điền bảng metric sau:

| Model/checkpoint | MCD | WER | CER | MOS mean | MOS std |
|---|---:|---:|---:|---:|---:|
| Baseline (original) | [ ] | [ ] | [ ] | [ ] | [ ] |
| Fine-tuned (best) | [ ] | [ ] | [ ] | [ ] | [ ] |

### 5.3 So sánh giữa các cấu hình VieNeu-TTS

| Setup | Data size | Text normalization | Trim silence | MCD | WER | CER | MOS |
|---|---:|---|---|---:|---:|---:|---:|
| Baseline original | 100% | N/A | N/A | [ ] | [ ] | [ ] | [ ] |
| Full pipeline | 100% | Yes | Yes | [ ] | [ ] | [ ] | [ ] |
| No text normalization | 100% | No | Yes | [ ] | [ ] | [ ] | [ ] |
| No trim silence | 100% | Yes | No | [ ] | [ ] | [ ] | [ ] |
| Reduced data | 50% | Yes | Yes | [ ] | [ ] | [ ] | [ ] |

---

## 6. Thảo luận và phân tích lỗi

### 6.1 Overfitting / underfitting
- Đối chiếu train/val/test.
- Nhận định trạng thái và lý do.
- Nếu cần: điều chỉnh regularization, early stopping, LR.

### 6.2 Phân tích trường hợp lỗi

| Audio ID | Ground truth text | Generated behavior | Error type | Hypothesis | Proposed fix |
|---|---|---|---|---|---|
| [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

Lỗi thường gặp cần phân loại:
- Nuốt chữ.
- Lặp từ.
- Sai ngắt nghỉ.
- Rè/robot/noise.
- Sai phát âm từ hiếm.

---

## 7. Kết luận và hướng phát triển

### 7.1 Tổng kết
- Pipeline đã xây dựng.
- Checkpoint tốt nhất.
- Metric chính và nhận xét chất lượng âm thanh.

### 7.2 Hạn chế
- Tiêu tốn tài nguyên.
- Nhạy cảm với chất lượng transcript.
- Nhạy cảm với alignment dữ liệu.

### 7.3 Hướng phát triển
- Mở rộng dữ liệu theo speaker/domain.
- Cải tiến text normalization theo luật tiếng Việt.
- Tối ưu infer latency và triển khai.

---

## 8. Yêu cầu trình bày và trích dẫn

### 8.1 Văn phong
- Khoa học, ngắn gọn, khách quan.

### 8.2 Hình/bảng
- Mỗi hình có chú thích bên dưới.
- Mỗi bảng có tiêu đề bên trên và đơn vị rõ ràng.

### 8.3 Trích dẫn
Cần trích dẫn đầy đủ:
- Model VieNeu-TTS.
- Base model (NeuTTS Air nếu được sử dụng trong model card).
- Dataset Kaggle.

Mẫu trích dẫn nhanh:
- VieNeu-TTS: https://huggingface.co/pnnbao-ump/VieNeu-TTS
- Dataset: https://www.kaggle.com/datasets/nhtlnguyn1106/xttsv2-finetuning-data-20260417

---

## 9. Phụ lục tracking kết quả (tích hợp từ template)

### 9.1 Run metadata

| Run ID | Phase | Date | Git commit | Seed | Device | Notes |
|---|---|---|---|---|---|---|
| [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

### 9.2 Hyperparameter record

| Run ID | LR | Batch size | Grad accum | Precision | Freeze modules | Scheduler | Early stopping patience |
|---|---|---|---|---|---|---|---|
| [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

### 9.3 Epoch tracking

| Run ID | Epoch | Train loss | Val loss | Best val so far | Checkpoint saved | Audio sample saved | Comment |
|---|---|---:|---:|---:|---|---|---|
| [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

### 9.4 Phase summary

| Phase | Start checkpoint | End checkpoint | Best checkpoint | Best val loss | Stop reason |
|---|---|---|---|---:|---|
| Phase 1 (warmup) | [ ] | [ ] | [ ] | [ ] | [ ] |
| Phase 2 (full finetune) | [ ] | [ ] | [ ] | [ ] | [ ] |
| Phase 3 (refine) | [ ] | [ ] | [ ] | [ ] | [ ] |

### 9.5 Final model selection note
- Selected checkpoint: [ ]
- Why selected: [ ]
- Trade-off observed: [ ]
- Ready for deployment: [Yes/No]
