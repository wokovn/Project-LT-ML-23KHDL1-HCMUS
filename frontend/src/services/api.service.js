import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

class ApiService {
  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  async search(query, options = {}) {
    const response = await this.client.post('/search', { 
      query, 
      language: options.language,
      freshness: options.freshness
    });
    return response.data;
  }

  async searchAndSummarize(query, options = {}) {
    const response = await this.client.post('/search-summarize', { 
      query, 
      language: options.language,
      freshness: options.freshness
    });
    return response.data;
  }

  async scrapeAndSummarize(urls) {
    const response = await this.client.post('/scrape-summarize', { urls });
    return response.data;
  }

  async scrape(url) {
    const response = await this.client.post('/scrape', { url });
    return response.data;
  }

  async generateWithGemini(prompt) {
    const response = await this.client.post('/gemini', { prompt });
    return response.data;
  }

  async summarizeNews(content, title) {
    const response = await this.client.post('/gemini/summarize', { content, title });
    return response.data;
  }

  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export default new ApiService();
