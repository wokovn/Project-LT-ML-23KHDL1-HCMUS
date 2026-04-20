### Giai đoạn 1: Khảo sát Mô hình (Model Profiling)

- **Phạm vi nhiệm vụ cá nhân:** Chỉ thực hiện một hướng fine-tune trên VieNeu-TTS. Phần so sánh chéo nhiều mô hình là phần tổng hợp ở mức nhóm; báo cáo cá nhân tập trung so sánh nội bộ giữa checkpoint gốc và checkpoint fine-tune.

- **Tải model:** Tải trọng số của VieNeu-TTS về môi trường local hoặc server.
    
- **Chạy test thử (Inference Test):** Khởi chạy mô hình với một vài câu văn bản mẫu để kiểm tra pipeline hoạt động.
    
- **Xác định Input/Output Format:**
    
    - _Text Input:_ Kiểm tra xem mô hình nhận text thô hay cần chuyển sang phoneme (thường XTTSv2 có tokenizer xử lý trực tiếp text).
        
    - _Speaker Conditioning (Bổ sung):_ Xác định cơ chế clone giọng. Tìm hiểu cách truyền **Speaker Reference Audio** (file âm thanh mẫu 3-5 giây) hoặc cách trích xuất Speaker Embedding đầu vào.
        
    - _Output:_ Xác nhận đầu ra là waveform (vì XTTSv2 đã tích hợp sẵn DVAE/HiFi-GAN làm vocoder bên trong, không cần vocoder ngoài).
        

### Giai đoạn 2: Hiệu chỉnh & Chuẩn hóa Dữ liệu (Dataset Alignment)

- **Đối chiếu cấu hình:** Chốt một bộ thông số âm thanh cố định theo config chạy thực tế trước khi tiền xử lý (khuyến nghị 24000Hz, Mono) và giữ nhất quán cho toàn bộ train/validation/test.
    
- **Chuẩn hóa Dataset:**
    
    - _Resampling (Bổ sung):_ Convert toàn bộ audio trong tập dataset Kaggle về đúng Sampling rate và định dạng Mono của model.
        
    - _Trim silence (Bổ sung):_ Cắt bỏ phần khoảng lặng (silence) thừa ở đầu và cuối mỗi file audio để tránh lỗi mô hình ngắt nghỉ quá lâu khi sinh giọng.
        
    - _Text Normalization:_ Xử lý viết tắt, số đếm, và dấu câu cho khớp với transcript.
        
- **Sanity Check:** Chạy thử dataset đã chuẩn hóa qua DataLoader để xem có lỗi mismatch kích thước tensor không.

- **Khóa chia tập dữ liệu & chống rò rỉ (critical):** Cố định file split ngay từ đầu (train/validation/test), không reshuffle giữa các lần chạy; nếu có nhiều speaker thì ưu tiên tách theo speaker để giảm leakage.

- **Gắn phiên bản dữ liệu:** Lưu version dataset Kaggle, timestamp tải dữ liệu và commit xử lý dữ liệu để đảm bảo tái lập.
    

### Giai đoạn 3: Chiến lược Train (Fine-tuning Strategy)

- **Train nháp:** Chạy thử 1-2 epoch nghiệm thu (sanity check training) để đảm bảo không có lỗi code, loss giảm nhẹ và pipeline lưu file hoạt động tốt.

- **Thiết lập tái lập (critical):** Cố định seed cho Python/NumPy/PyTorch, lưu đầy đủ config mỗi run (LR, batch size, freeze strategy, scheduler) để có thể chạy lại và đối chiếu kết quả.
    
- **Chia Phase Huấn luyện (Làm rõ các block chặn):**
    
    - _Phase 1: Warm-up._ Đóng băng (freeze) phần DVAE và Vocoder (vì đã tốt sẵn). Chỉ mở khóa (unfreeze) **GPT Model** (để học cách phát âm, ngắt nghỉ) và **Decoder**. Sử dụng learning rate khởi tạo an toàn.
        
    - _Phase 2: Full finetune._ Mở khóa thêm các layer cần thiết (nếu có) và train với learning rate chuẩn định sẵn để mô hình hội tụ.
        
    - _Phase 3: Refine._ Hạ learning rate (Low LR) để tinh chỉnh các chi tiết nhỏ, giúp giọng mượt hơn.
        

### Giai đoạn 4: Quản lý Log & Lưu trữ (Logging & Checkpointing)

- **Theo dõi Metric:** Ghi lại Loss của tập Train và tập Validation theo từng epoch (ghi đầy đủ tham số để dùng vẽ chart Learning Curve cho báo cáo).
    
- **Lưu Checkpoint (Cải tiến):** Chỉ lưu **Top-K checkpoints tốt nhất** (dựa trên Validation Loss thấp nhất) và checkpoint của epoch cuối cùng để tránh làm đầy ổ cứng, vì file model rất nặng.
    
- **Lưu Audio Sample:** Generate audio mỗi epoch từ một tập 5 câu cố định (fixed test sentences) để theo dõi sự tiến bộ.

- **lưu trạng thái của Optimizer (Optimizer state)**: chuyển từ phase 2 sang phase 3 sẽ giúp quá trình huấn luyện mượt mà hơn, tránh hiện tượng gradient bị dao động mạnh

- **Lưu manifest môi trường:** Ghi lại version Python, CUDA, torch, TTS và driver NVIDIA tương ứng với từng run.
    

### Giai đoạn 5: Đánh giá Định kỳ (Validation Check)

- **Quy trình kiểm tra (Sau mỗi vài epoch):**
    
    - Generate audio từ 5 câu test cố định.
        
    - Dựa trên Validation Loss kết hợp với việc nghe thử audio.
        
    - Điều kiện dừng (Early Stopping): Dừng khi Validation loss không giảm trong một số epoch liên tiếp (patience).
        
- **Checklist Nghe thử:**
    
    - Phát âm có đúng chữ không?
        
    - Có bị rè, nhiễu âm hay có giọng robot không?
        
    - Ngắt câu có đúng nhịp điệu tự nhiên không?
        
    - _Bổ sung:_ Có bị **nuốt chữ** hoặc **lặp từ** không? (Lỗi kinh điển của các mô hình auto-regressive như XTTS).
        

### Giai đoạn 6: Phân tích Thực nghiệm & So sánh (Ablation & Evaluation)

- **Đánh giá Khách quan:** Tính toán các metric định lượng như MCD (Mel Cepstral Distortion) và WER/CER (để đo độ chính xác văn bản sinh ra).
    
- **Đánh giá Chủ quan (Bổ sung):** Tận dụng nhóm 5 người của bạn để tiến hành đo điểm MOS (Mean Opinion Score). Cho các thành viên nghe chéo các file kết quả và chấm điểm độ tự nhiên (1-5).
    
- **Thực nghiệm cắt bỏ (Ablation Study):** Đánh giá các yếu tố tác động đến kết quả:
    
    - Baseline nội bộ: Mô hình VieNeu gốc (Không finetune).
        
    - Giảm dung lượng dataset (VD: train với 50% data).
        
    - Không chuẩn hóa text (Không normalize text).
        
    - Không loại bỏ nhiễu/trim silence ở data.
        
- **Phân tích Lỗi sâu (Debug & Report):**
    
    - Tổng hợp các trường hợp lỗi ở tập Test (lỗi vỡ tiếng, lỗi phát âm sai).
        
    - Đưa ra giả thuyết tại sao lỗi (do audio gốc bị nhiễu, từ hiếm, hay độ dài câu quá quy định).
        
    - Đưa các số liệu, biểu đồ và phân tích này vào đúng các mục tương ứng trong file main.pdf.

- **Phạm vi đánh giá:** Báo cáo cá nhân chỉ đánh giá trên một hướng VieNeu-TTS fine-tune; không mở rộng sang thử nghiệm thêm mô hình khác.

### Chi tiết phần cứng:
1x RTX 3090 - 24 GB
CPU: Xeon® E5-2630 v4 | 20 Cores
RAM: 125.88 GB
DISK: 591 GB
Mạng: 764.4/1815.8 Mbps
Tốc độ ổ đĩa: 1889 MB/s
CUDA: 12.6
Vị trí: CA
Uptime: 99.43%