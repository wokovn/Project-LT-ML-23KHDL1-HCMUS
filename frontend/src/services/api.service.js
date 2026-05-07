import axios from 'axios';

const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const API_URL = (() => {
  const trimmedUrl = rawApiUrl.replace(/\/+$/, '');

  try {
    const parsedUrl = new URL(trimmedUrl);

    // If only an origin is provided, default to the backend API namespace.
    if (!parsedUrl.pathname || parsedUrl.pathname === '/') {
      parsedUrl.pathname = '/api';
      return parsedUrl.toString().replace(/\/+$/, '');
    }

    return trimmedUrl;
  } catch {
    // Support relative API URLs while keeping explicit path configuration intact.
    if (!trimmedUrl || trimmedUrl === '.') return '/api';
    return trimmedUrl.startsWith('/') ? trimmedUrl : `/${trimmedUrl}`;
  }
})();

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

  async scrapeAndSummarize(urls, query = '') {
    const response = await this.client.post('/scrape-summarize', { urls, query });
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

  async createTtsJob(text, options = {}) {
    const response = await this.client.post('/tts/jobs', {
      text,
      language: options.language || 'vi',
      speaker_audio: options.speakerAudio
    });
    return response.data;
  }

  async getTtsJob(key) {
    const response = await this.client.get(`/tts/jobs/${encodeURIComponent(key)}`);
    return response.data;
  }
}

export default new ApiService();
