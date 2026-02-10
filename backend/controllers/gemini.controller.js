import geminiService from '../services/gemini.service.js';

class GeminiController {
  async generate(req, res) {
    try {
      const { prompt } = req.body;
      
      if (!prompt) {
        return res.status(400).json({ error: 'Prompt is required' });
      }

      const data = await geminiService.generateContent(prompt);
      res.json(data);
    } catch (error) {
      console.error('Gemini Error:', error.message);
      res.status(500).json({ 
        error: 'Failed to generate content',
        details: error.message 
      });
    }
  }

  async summarize(req, res) {
    try {
      const { content, title } = req.body;
      
      if (!content) {
        return res.status(400).json({ error: 'Content is required' });
      }

      const data = await geminiService.summarizeNews(content, title);
      res.json(data);
    } catch (error) {
      console.error('Gemini Summarize Error:', error.message);
      res.status(500).json({ 
        error: 'Failed to summarize content',
        details: error.message 
      });
    }
  }
}
export default new GeminiController();