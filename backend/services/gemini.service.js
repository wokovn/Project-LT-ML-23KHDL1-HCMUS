import { GoogleGenerativeAI } from '@google/generative-ai';
import geminiConfig from '../config/gemini.config.js';

class GeminiService {
  constructor() {
    if (!geminiConfig.API_KEY) {
      console.warn('Gemini API key not configured');
    } else {
      this.genAI = new GoogleGenerativeAI(geminiConfig.API_KEY);
    }
  }

  async generateContent(prompt) {
    if (!geminiConfig.API_KEY) {
      throw new Error('Gemini API key not configured');
    }

    const model = this.genAI.getGenerativeModel({ model: geminiConfig.MODEL });
    const result = await model.generateContent(prompt);
    const response = await result.response;
    const text = response.text();

    return { text };
  }

  async summarizeNews(content, title = '') {
    if (!geminiConfig.API_KEY) {
      throw new Error('Gemini API key not configured');
    }

    const customInstruction = `
    Đóng vai: Biên tập viên Ban Thời sự - Đài Truyền hình Việt Nam (VTV).
    Nhiệm vụ: Biên tập lại nội dung tin tức dưới đây thành một bản tin thời sự ngắn.

    Yêu cầu biên tập:
    1. Văn phong: Chính luận, trang trọng, gãy gọn, dứt khoát (đặc trưng của bản tin Thời sự 19h).
    2. Cấu trúc:
    - Mở đầu trực diện vào vấn đề (dùng các động từ mạnh).
    - Thân bài tóm lược diễn biến chính/số liệu quan trọng nhất.
    - Kết thúc (nếu có) nêu bật ý nghĩa hoặc định hướng tiếp theo.
    3. Độ dài: Khoảng 150-200 từ (tương đương 30-45 giây đọc).
    4. Tuyệt đối khách quan, không lồng ghép cảm xúc cá nhân, giữ nguyên các thuật ngữ chuyên môn nếu cần thiết.

    Dữ liệu đầu vào:
    - Tiêu đề gốc: ${title}
    - Nội dung gốc:
    ${content}

Hãy bắt đầu bản tin:
`;

    const model = this.genAI.getGenerativeModel({ model: geminiConfig.MODEL });
    const result = await model.generateContent(customInstruction);
    const response = await result.response;
    const text = response.text();

    return { summary: text };
  }

  async summarizeMultipleNews(articles) {
    if (!geminiConfig.API_KEY) {
      throw new Error('Gemini API key not configured');
    }

    // Format tất cả các bài báo thành 1 prompt
    let formattedContent = `Đóng vai: Biên tập viên Ban Thời sự - Đài Truyền hình Việt Nam (VTV).
Nhiệm vụ: Dưới đây là ${articles.length} bài tin tức. Hãy biên tập lại TOÀN BỘ các tin này thành một bản tin tổng hợp ngắn gọn.

Yêu cầu biên tập:
1. Văn phong: Chính luận, trang trọng, gãy gọn, dứt khoát (đặc trưng của bản tin Thời sự 19h).
2. Cấu trúc:
   - Nhóm các tin liên quan lại với nhau (nếu có).
   - Mỗi tin được tóm lược thành 2-3 câu, rõ ràng, dễ hiểu.
3. Độ dài: Mỗi tin khoảng 50-80 từ.
4. Tuyệt đối khách quan, không lồng ghép cảm xúc cá nhân.
5. Loại bỏ các bài trùng nội dung nếu có.
6. Chỉ trả về nội dung bài nói, bắt đầu bằng cách nói bản tổng hợp này có gì, các đoạn sau
đọc phải có câu chuyển (ví dụ: "Tiếp theo là tin về...", "Chuyển sang tin tiếp theo...", "Tin cuối cùng...") và topic sentence.
7. Không chú thích gì cả, phản hồi trông như lời nói của biên tập viên
---
DỮ LIỆU ĐẦU VÀO:

`;

    articles.forEach((article, index) => {
      formattedContent += `\n[BÀI ${index + 1}]\n`;
      formattedContent += `Tiêu đề: ${article.title}\n`;
      formattedContent += `Nguồn: ${article.source}\n`;
      formattedContent += `Nội dung:\n${article.content}\n`;
      formattedContent += `\n---\n`;
    });

    formattedContent += `\n\nHãy bắt đầu bản tin tổng hợp:`;

    const model = this.genAI.getGenerativeModel({ model: geminiConfig.MODEL });
    const result = await model.generateContent(formattedContent);
    const response = await result.response;
    const text = response.text();

    return { summary: text, totalArticles: articles.length };
  }
}

export default new GeminiService();
