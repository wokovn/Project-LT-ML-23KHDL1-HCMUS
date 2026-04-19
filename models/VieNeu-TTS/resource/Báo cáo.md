### Giai đoạn 1: Khảo sát Mô hình (Model Profiling)

Giai đoạn này cung cấp vật liệu để bạn hoàn thiện phần mở đầu và định hình kiến trúc.

- **Mục 1 - Giới thiệu bài toán:** Nêu bối cảnh ứng dụng TTS thực tế. Phát biểu rõ đây là bài toán sinh giọng nói. Xác định mục tiêu đầu ra (waveform) và các tiêu chí đánh giá chính.
    
- **Mục 3.1 - Phạm vi mô hình trong báo cáo cá nhân:** Chỉ trình bày một mô hình VieNeu-TTS (XTTSv2). Thiết lập baseline nội bộ là checkpoint gốc (không fine-tune) và so sánh với checkpoint fine-tune. (Phần so sánh nhiều mô hình là phần tổng hợp ở mức nhóm.)
    
- **Mục 3.2 - Lý do lựa chọn mô hình:** Giải thích sự phù hợp của XTTSv2 (khả năng zero-shot, có sẵn tiếng Việt).
    
- **Mục 3.3 - Kiến trúc chi tiết:** Chèn sơ đồ kiến trúc XTTSv2 (luồng Text/Audio vào -> output ra). Mô tả số tham số, hàm kích hoạt và kích thước đầu vào/đầu ra.
    
- **Mục 8 - Yêu cầu trình bày:** Ghi chú lại link HuggingFace của VieNeu-TTS để trích dẫn nguồn đầy đủ.
    

### Giai đoạn 2: Hiệu chỉnh & Chuẩn hóa Dữ liệu (Dataset Alignment)

**Mục 2.1 - Nguồn dữ liệu và mô tả**: Trình bày tập XTTSv2 Finetuning Data 20260417 từ Kaggle (khoảng 7.81 GB, ~14.5k files). Mô tả rõ các tệp metadata.csv, train_wav.csv, eval.csv, test_wav.csv và thư mục wavs.


**Mục 2.2 - Chia tập dữ liệu**: Sử dụng trực tiếp split có sẵn train_wav.csv / eval.csv / test_wav.csv để cố định train/validation/test cho mọi thực nghiệm (không reshuffle giữa các lần chạy). Ghi rõ lý do: đảm bảo công bằng khi so sánh các lần fine-tune và giảm rủi ro data leakage.

**2.3 Tiền xử lý dữ liệu** Do sử dụng kiến trúc đặc thù của XTTSv2 (VieNeu-TTS), nhóm không chỉ làm sạch dữ liệu thông thường mà tiến hành hiệu chỉnh dữ liệu (alignment) để tương thích tuyệt đối với cấu hình đầu vào của mô hình. Cụ thể:

- **Đồng bộ hóa tín hiệu âm thanh:** Toàn bộ tập dữ liệu âm thanh được chuyển đổi (resample) về tần số lấy mẫu 24000 Hz (theo config chạy thực tế) và định dạng Mono. Điều này nhằm khớp với thông số của bộ Vocoder nội bộ (HiFi-GAN/DVAE) trong kiến trúc XTTS, tránh lỗi sai lệch chiều dữ liệu (tensor dimension mismatch) khi huấn luyện.
    
- **Cắt dải băng rác (Trim Silence):** Áp dụng thuật toán Voice Activity Detection (VAD) để loại bỏ tuyệt đối khoảng lặng vô thanh ở đầu và cuối mỗi file audio. Việc này giúp mô hình ngôn ngữ (GPT) bên trong XTTS không bị đánh lừa bởi các nhiễu im lặng, từ đó giải quyết triệt để lỗi mô hình ngắt nghỉ quá lâu hoặc ngập ngừng khi sinh giọng điệu.
    
- **Chuẩn hóa văn bản đầu vào:** Xây dựng bộ quy tắc (Regular Expressions) để ánh xạ toàn bộ chữ số và từ viết tắt sang dạng văn bản đọc tường minh (Ví dụ: "TP.HCM" $\rightarrow$ "thành phố hồ chí minh"). Vì XTTS xử lý văn bản trực tiếp qua Tokenizer thay vì dùng Phoneme ngoài, bước này đảm bảo mô hình học được đúng cách phát âm tự nhiên của tiếng Việt.
    

_Nhận xét tác động kỳ vọng:_ Việc đồng bộ hóa khắt khe này giúp rút ngắn thời gian hội tụ của mô hình ở Phase 1, đồng thời loại bỏ các lỗi "ảo giác" (hallucination) thường gặp ở các mô hình TTS tự hồi quy.
    

### Giai đoạn 3 & 4: Chiến lược Train & Quản lý Log

Dữ liệu từ lúc cấu hình chạy code và log kết quả sẽ được đưa vào **Mục 4** và một phần **Mục 5**.

- **Mục 4.1 - Hàm mất mát:** Nêu hàm mất mát được sử dụng (ví dụ: Mel-loss) và giải thích lý do phù hợp.
    
- **Mục 4.2 - Thuật toán tối ưu:** Trình bày bộ tối ưu (ví dụ: AdamW). Ghi rõ learning rate và scheduler cho 3 phase (Warm-up, Full finetune, Refine) cùng tiêu chí dừng sớm (Early Stopping).
    
- **Mục 4.3 - Siêu tham số:** Liệt kê batch size, epochs, chiến lược đóng băng (freeze) các block của model. Nêu cấu hình phần cứng huấn luyện.
    - Chi tiết phần cứng.
    - Nêu rõ chiến lược tinh chỉnh siêu tham số: thử nghiệm thủ công có kiểm soát (controlled manual search), giữ nguyên split dữ liệu và chỉ thay đổi 1 nhóm tham số mỗi lần chạy.
    
- **Mục 5.1 - Biểu đồ quá trình học:** Lấy log từ thư mục checkpoint để trình bày biểu đồ Loss trên Train/Validation theo từng epoch. Nhận xét xu hướng hội tụ.
    - Bổ sung thông tin tái lập: seed sử dụng, version thư viện chính, ID run/checkpoint tốt nhất.
    

### Giai đoạn 5 & 6: Đánh giá, Thực nghiệm & Phân tích lỗi sâu

Đây là phần thể hiện tư duy phân tích của nhóm, gom vào **Mục 5 (còn lại), Mục 6 và Mục 7**.

- **Mục 5.2 - Đánh giá trên tập kiểm tra:** Báo cáo các chỉ số định lượng (MCD, WER) và điểm đánh giá chủ quan (MOS).
    
- **Mục 5.3 - So sánh giữa các cấu hình VieNeu-TTS:** Lập bảng so sánh hiệu năng giữa checkpoint gốc và checkpoint fine-tune, kèm kết quả thực nghiệm cắt bỏ (không chuẩn hóa text, giảm data, không trim silence).
    
- **Mục 6.1 - Đánh giá hiện tượng overfitting/underfitting:** Đối chiếu kết quả Train/Val/Test để kết luận trạng thái mô hình.
    
- **Mục 6.2 - Phân tích trường hợp dự đoán sai:** Kinh nghiệm phân tích và đánh giá nhãn lỗi từ tập 3000 dữ liệu đánh giá mô hình trước đây của bạn sẽ rất hữu dụng lúc này. Chọn các audio test bị sinh lỗi (vỡ tiếng, đọc sai chữ, nuốt từ) để phân tích. Đưa ra giả thuyết nguyên nhân do nhiễu, đặc trưng âm thanh hay văn bản. Gợi ý hướng cải thiện.
    
- **Mục 7 - Kết luận và hướng phát triển:** Tóm tắt quy trình, kết quả nổi bật, mô hình tốt nhất. Nêu hạn chế (ví dụ tốn resource) và đề xuất mở rộng.