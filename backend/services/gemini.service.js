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
    Nhiệm vụ: Dưới đây là bài tin tức. Hãy biên tập lại TOÀN BỘ các tin này thành một bản tin tổng hợp ngắn gọn.

Yêu cầu biên tập:
0. Chỉ lấy nội dung dài nhất của một bài viết để tóm tắt, tránh bị lạc đề do quảng cáo trong bài.
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
8. Không dùng formal markdown, chỉ phản hồi thuần văn bản.

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

  async summarizeMultipleNews(articles, query = '') {
    if (!geminiConfig.API_KEY) {
      throw new Error('Gemini API key not configured');
    }

    // Format tất cả các bài báo thành 1 prompt
    let formattedContent = `Đóng vai: Biên tập viên Ban Thời sự - Đài Truyền hình Việt Nam (VTV).
Từ khóa tìm kiếm: "${query}"
Nhiệm vụ: Dưới đây là ${articles.length} bài tin tức. Hãy biên tập lại TOÀN BỘ các tin này thành một bản tin tổng hợp ngắn gọn.

Yêu cầu biên tập:
0. **QUAN TRỌNG**: Kiểm tra độ liên quan:
   - Nếu nội dung các bài báo KHÔNG liên quan đến từ khóa tìm kiếm "${query}", hãy DỪNG LẠI và chỉ trả về: "Không tìm được bài viết liên quan đến từ khóa này."
   - Chỉ tiếp tục tóm tắt nếu các bài báo CÓ LIÊN QUAN đến từ khóa.
   - Chỉ lấy nội dung dài nhất của một bài viết để tóm tắt, tránh bị lạc đề do quảng cáo trong bài.
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
8. Không dùng formal markdown, chỉ phản hồi thuần văn bản.
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
    
    // Check if response was blocked due to safety filters
    if (!response.candidates || response.candidates.length === 0) {
      throw new Error('PROHIBITED_CONTENT: Nội dung bị chặn bởi bộ lọc an toàn của Gemini AI');
    }
    
    const candidate = response.candidates[0];
    if (candidate.finishReason === 'SAFETY') {
      const safetyRatings = candidate.safetyRatings || [];
      console.log('[GEMINI API] Content blocked by safety filters:', safetyRatings);
      throw new Error('PROHIBITED_CONTENT: Nội dung vi phạm tiêu chuẩn an toàn');
    }
    
    let text;
    try {
      text = response.text();
    } catch (textError) {
      if (textError.message.includes('PROHIBITED_CONTENT') || textError.message.includes('blocked')) {
        throw new Error('PROHIBITED_CONTENT: Nội dung không phù hợp được phát hiện');
      }
      throw textError;
    }

    return { summary: text, totalArticles: articles.length };
  }
}

export default new GeminiService();
