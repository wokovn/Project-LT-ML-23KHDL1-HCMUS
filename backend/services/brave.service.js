import axios from 'axios';
import braveConfig from '../config/brave.config.js';

class BraveService {
  async search(query, options = {}) {
    if (!braveConfig.API_KEY) {
      throw new Error('Brave API key not configured');
    }

    const params = {
      q: query,
      search_lang: options.language || 'vi',
      count: 10
    };

    // Add freshness filter if provided
    if (options.freshness) {
      params.freshness = options.freshness;
    }

    console.log('[BRAVE API] Request params:', JSON.stringify(params, null, 2));

    const response = await axios.get(braveConfig.BASE_URL, {
      params,
      headers: {
        'Accept': 'application/json',
        'X-Subscription-Token': braveConfig.API_KEY
      }
    }).catch(err => {
      if (err.response?.status === 429) {
        throw new Error('Brave API rate limit exceeded. Please try again later.');
      }
      throw err;
    });

    console.log('[BRAVE API] Response keys:', Object.keys(response.data));
    console.log('[BRAVE API] Has news results:', !!response.data.news?.results);
    console.log('[BRAVE API] Has web results:', !!response.data.web?.results);
    if (response.data.news?.results) {
      console.log('[BRAVE API] News results count:', response.data.news.results.length);
    }
    if (response.data.web?.results) {
      console.log('[BRAVE API] Web results count:', response.data.web.results.length);
    }

    return response.data;
  }
}

export default new BraveService();
