import axios from 'axios';
import ttsConfig from '../config/tts.config.js';

class TtsService {
  constructor() {
    this.client = axios.create({
      baseURL: ttsConfig.SERVICE_URL,
      timeout: ttsConfig.TIMEOUT_MS
    });
  }

  async health() {
    const response = await this.client.get('/health');
    return response.data;
  }

  async synthesize(payload) {
    const response = await this.client.post('/v1/tts', payload);
    return response.data;
  }

  async createTask(payload) {
    const response = await this.client.post('/v1/tasks/tts', payload);
    return response.data;
  }

  async getTask(taskId) {
    const response = await this.client.get(`/v1/tasks/${encodeURIComponent(taskId)}`);
    return response.data;
  }
}

export default new TtsService();
