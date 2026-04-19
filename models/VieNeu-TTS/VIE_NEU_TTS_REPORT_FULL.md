# BÁO CÁO NGHIÊN CỨU SƠ BỘ
## Fine-tune VieNeu-TTS cho bài toán Text-to-Speech tiếng Việt

## Tóm tắt
Báo cáo này trình bày kết quả kiểm định và chuẩn hóa dữ liệu trước huấn luyện cho bài toán fine-tune VieNeu-TTS trên bộ XTTSv2 Finetuning Data 20260417 tại thư mục cục bộ `D:/HCMUS/data_project_LT/archive`. Quy trình gồm hai giai đoạn: (i) smoke gate strict trên dữ liệu gốc, và (ii) chuẩn hóa toàn bộ dữ liệu về định dạng huấn luyện mục tiêu (24000 Hz, mono). Kết quả cho thấy dữ liệu gốc không có lỗi thiếu file theo metadata, nhưng có tỷ lệ lệch sample rate và số kênh cao ở cả train/eval/test. Sau chuẩn hóa, toàn bộ split vượt gate strict với tỷ lệ lỗi bằng 0 trên các tiêu chí missing file, sample-rate mismatch và channel mismatch. Kết luận thực nghiệm: chuẩn hóa stage 2 là bước bắt buộc để đảm bảo dữ liệu phù hợp cho Phase 1.

## 1. Bối cảnh và câu hỏi nghiên cứu
Mục tiêu nghiên cứu là xác nhận mức độ sẵn sàng của dữ liệu trước khi khởi chạy Phase 1 cho VieNeu-TTS theo nguyên tắc “data gate before training”. Câu hỏi trung tâm: dữ liệu tại nguồn cục bộ đã đủ điều kiện kỹ thuật để train ngay hay cần chuẩn hóa thêm để giảm rủi ro runtime và nhiễu học.

## 2. Dữ liệu và phương pháp

### 2.1 Nguồn dữ liệu
- Dataset: XTTSv2 Finetuning Data 20260417 (Kaggle).
- Đường dẫn kiểm định: `D:/HCMUS/data_project_LT/archive`.
- File split dùng cho gate: `train_wav.csv`, `eval.csv`, `test_wav.csv`.
- Ràng buộc đầu vào cho train: 24000 Hz, mono.

### 2.2 Thiết kế kiểm thử giai đoạn 1
Smoke check strict được chạy trên 256 mẫu ngẫu nhiên cho mỗi split với các tiêu chí:
1. `missing_files`: CSV có trỏ tới file audio thực hay không.
2. `sr_mismatch`: sample rate có khớp 24000 Hz hay không.
3. `channel_mismatch`: số kênh có khớp mono hay không.

### 2.3 Thiết kế chuẩn hóa giai đoạn 2
Chuẩn hóa toàn bộ dữ liệu theo pipeline:
1. Đọc và xác thực file tham chiếu từ các CSV split.
2. Resample audio về 24000 Hz.
3. Chuyển audio về 1 kênh.
4. Ghi lại CSV đầu ra trong thư mục chuẩn hóa và chạy lại smoke strict hậu kiểm.

Thư mục đầu ra stage 2: `D:/HCMUS/data_project_LT/xtts_stage2_24k_mono`.

## 3. Kết quả

### 3.1 Kết quả smoke gate strict trên dữ liệu gốc

| Split | checked | missing_files | sr_mismatch | channel_mismatch | empty_text | avg_duration_sec | min_duration_sec | max_duration_sec | Kết luận |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| train_wav.csv | 256 | 0 | 171 | 85 | 0 | 6.433 | 0.86 | 22.93 | Không đạt |
| eval.csv | 256 | 0 | 177 | 79 | 0 | 6.913 | 0.85 | 60.18 | Không đạt |
| test_wav.csv | 256 | 0 | 176 | 80 | 0 | 6.731 | 0.61 | 28.06 | Không đạt |

Diễn giải:
- Tính toàn vẹn metadata-audio đã tốt (`missing_files = 0` ở cả ba split).
- Tuy nhiên, sai lệch định dạng audio vẫn lớn (sample rate lệch khoảng 67-69%, channel lệch khoảng 31-33% trên mẫu kiểm định), nên chưa đủ điều kiện vào train.

### 3.2 Tác động của chuẩn hóa stage 2 trên toàn bộ dữ liệu

| Split | rows_total | rows_kept | dropped_missing | dropped_invalid | sr_converted | ch_converted |
|---|---:|---:|---:|---:|---:|---:|
| train_wav.csv | 11579 | 11579 | 0 | 0 | 8163 | 3416 |
| eval.csv | 1446 | 1446 | 0 | 0 | 1019 | 427 |
| test_wav.csv | 1450 | 1450 | 0 | 0 | 1023 | 427 |

Diễn giải:
- Không có dòng nào bị loại ở bước stage 2 trên dữ liệu ổ D.
- Pipeline chỉ thực hiện chuyển đổi định dạng với quy mô lớn, đúng với kỳ vọng từ kết quả stage 1.

### 3.3 Hậu kiểm strict sau chuẩn hóa

| Split | checked | missing_files | sr_mismatch | channel_mismatch | empty_text | avg_duration_sec | min_duration_sec | max_duration_sec | Kết luận |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| train_wav.csv | 256 | 0 | 0 | 0 | 0 | 6.434 | 0.86 | 22.93 | Đạt |
| eval.csv | 256 | 0 | 0 | 0 | 0 | 6.914 | 0.85 | 60.18 | Đạt |
| test_wav.csv | 256 | 0 | 0 | 0 | 0 | 6.731 | 0.61 | 28.06 | Đạt |

Toàn bộ gate kỹ thuật đã đạt ở chế độ strict.

## 4. Thảo luận

### 4.1 Hàm ý phương pháp luận
Kết quả khẳng định rằng với bộ dữ liệu này, vấn đề chính trước huấn luyện không nằm ở thiếu file metadata mà nằm ở không đồng nhất định dạng tín hiệu. Vì vậy, bước chuẩn hóa audio cần được xem là một phần mặc định của pipeline thay vì thao tác tùy chọn.

### 4.2 Rủi ro nếu bỏ qua stage 2
Bỏ qua chuẩn hóa có thể gây ra:
1. Lỗi tương thích khi load batch do sample rate/channel không đồng nhất.
2. Gia tăng nhiễu tối ưu vì mô hình học trên phân bố tín hiệu không chuẩn.
3. Khó quy chiếu nguyên nhân khi chất lượng đầu ra giảm.

### 4.3 Giới hạn hiện tại
Báo cáo này dừng ở giai đoạn dữ liệu và chưa chạy huấn luyện, do đó chưa có chỉ số mô hình như val loss trajectory, WER, CER, MCD hoặc MOS.

## 5. Trạng thái sẵn sàng cho Phase 1

### 5.1 Kết luận sẵn sàng
- Data gate: Pass strict trên train/eval/test sau chuẩn hóa.
- Data root đề xuất cho train: `D:/HCMUS/data_project_LT/xtts_stage2_24k_mono`.
- Điều kiện tiền đề cho Phase 1: Đã đạt.

### 5.2 Checklist chuyển sang huấn luyện
1. Khóa cấu hình Phase 1 bằng snapshot config tại thời điểm chạy.
2. Xác nhận entrypoint train thực tế (biến `TRAIN_SCRIPT`) trước khi chạy script warmup.
3. Chạy smoke train ngắn và lưu artifact đầy đủ (`checkpoints`, `logs`, `samples`, `metrics`).

## 6. Kết luận
Với dữ liệu tại ổ D, quy trình kiểm định cho thấy tập gốc không còn lỗi tham chiếu file nhưng chưa đạt điều kiện train do sai lệch định dạng audio ở mức lớn. Chuẩn hóa stage 2 đã chuyển toàn bộ dữ liệu về đúng chuẩn 24k mono, không làm mất dữ liệu, và giúp dữ liệu vượt gate strict hoàn toàn. Đây là cơ sở kỹ thuật đủ mạnh để bắt đầu Phase 1 theo workflow 3 phase.

## 7. Trích dẫn
- VieNeu-TTS: https://huggingface.co/pnnbao-ump/VieNeu-TTS
- Dataset XTTSv2 Finetuning Data 20260417: https://www.kaggle.com/datasets/nhtlnguyn1106/xttsv2-finetuning-data-20260417

## 8. Phụ lục theo dõi thực nghiệm

### 8.1 Nhật ký chạy chính

| Run ID | Nhóm bước | Date | Seed | Device | Kết quả |
|---|---|---|---|---|---|
| smoke_raw_d_drive_20260419 | gate_before_stage2 | 2026-04-19 | 20260419 | CPU | Fail (sr/channel mismatch, missing = 0) |
| stage2_normalize_d_drive_20260419 | stage2_data_norm | 2026-04-19 | N/A | CPU | Hoàn tất chuẩn hóa full về 24k mono |
| smoke_post_stage2_d_drive_20260419 | gate_after_stage2 | 2026-04-19 | 20260419 | CPU | Pass strict trên train/eval/test |

### 8.2 Trạng thái mô hình hiện tại
- Selected checkpoint: Chưa có (chưa chạy train).
- Trade-off observed: N/A.
- Ready for deployment: No.
