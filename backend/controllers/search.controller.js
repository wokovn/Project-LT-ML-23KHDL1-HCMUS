import braveService from '../services/brave.service.js';
import scrapeService from '../services/scrape.service.js';
import geminiService from '../services/gemini.service.js';
import pLimit from 'p-limit';

// Giới hạn concurrency - chỉ chạy 3 scrape cùng lúc (thay vì 10)
const scrapeLimit = pLimit(3);

class SearchController {
  async search(req, res) {
    try {
      const { query, language, freshness } = req.body;
      
      if (!query) {
        return res.status(400).json({ error: 'Query is required' });
      }

      const options = {};
      if (language) options.language = language;
      if (freshness) options.freshness = freshness;

      const data = await braveService.search(query, options);
      res.json(data);
    } catch (error) {
      console.error('Search Error:', error.message);
      res.status(500).json({ 
        error: 'Failed to perform search',
        details: error.response?.data || error.message 
      });
    }
  }

  async searchAndSummarize(req, res) {
    try {
      const { query, language, freshness } = req.body;
      
      if (!query) {
        return res.status(400).json({ error: 'Query is required' });
      }

      const options = {};
      if (language) options.language = language;
      if (freshness) options.freshness = freshness;

      // 1. Search bằng Brave
      console.log('[BRAVE API] Starting search request...');
      let searchData;
      try {
        searchData = await braveService.search(query, options);
        console.log('[BRAVE API] Search successful, found results');
      } catch (err) {
        console.error('[BRAVE API] ERROR:', err.message);
        console.error('[BRAVE API] Status:', err.response?.status);
        console.error('[BRAVE API] Details:', err.response?.data);
        
        if (err.response?.status === 429) {
          return res.status(429).json({ 
            error: 'Rate limit exceeded',
            api: 'Brave Search API',
            details: 'Vuot qua gioi han API Brave Search. Vui long thu lai sau it phut.' 
          });
        }
        throw err;
      }
      
      // 2. Lấy URLs từ kết quả (ưu tiên news, fallback về web)
      let urls = [];
      if (searchData.news?.results && searchData.news.results.length > 0) {
        urls = searchData.news.results.slice(0, 5).map(r => r.url);
      } else if (searchData.web?.results && searchData.web.results.length > 0) {
        urls = searchData.web.results
          .filter(r => r.type === 'search_result')
          .slice(0, 5)
          .map(r => r.url);
      }

      if (urls.length === 0) {
        return res.status(404).json({ error: 'Khong tim thay ket qua nao' });
      }

      // 3. Scrape tất cả URLs bằng Puppeteer
      console.log(`[PUPPETEER] Scraping ${urls.length} articles...`);
      const scrapePromises = urls.map(async (url, index) => {
        try {
          const scraped = await scrapeService.scrapeUrl(url);
          console.log(`[PUPPETEER] Successfully scraped: ${url}`);
          return {
            title: scraped.title || `Bai ${index + 1}`,
            source: new URL(url).hostname,
            content: scraped.text || '',
            url: url
          };
        } catch (err) {
          console.error(`[PUPPETEER] Failed to scrape ${url}:`, err.message);
          return null;
        }
      });

      const articles = (await Promise.all(scrapePromises)).filter(a => a !== null);
      console.log(`[PUPPETEER] Successfully scraped ${articles.length}/${urls.length} articles`);

      if (articles.length === 0) {
        return res.status(500).json({ error: 'Khong the scrape duoc bai bao nao' });
      }

      // 4. Gửi tất cả vào Gemini để tóm tắt
      console.log(`[GEMINI API] Starting summarization of ${articles.length} articles...`);
      let summary;
      try {
        summary = await geminiService.summarizeMultipleNews(articles, query);
        console.log('[GEMINI API] Summarization successful');
      } catch (err) {
        console.error('[GEMINI API] ERROR:', err.message);
        console.error('[GEMINI API] Status:', err.response?.status);
        console.error('[GEMINI API] Details:', err.response?.data);
        
        if (err.message.includes('PROHIBITED_CONTENT')) {
          return res.status(400).json({ 
            error: 'Prohibited content',
            api: 'Google Gemini API',
            details: 'Nội dung không phù hợp. Gemini AI đã chặn nội dung này vì vi phạm tiêu chuẩn an toàn.'
          });
        }
        
        if (err.response?.status === 429 || err.message.includes('429')) {
          return res.status(429).json({ 
            error: 'Rate limit exceeded',
            api: 'Google Gemini API',
            details: 'Vuot qua gioi han API Gemini. Vui long thu lai sau it phut.' 
          });
        }
        throw err;
      }

      console.log('[SUCCESS] Request completed successfully');
      res.json({
        summary: summary.summary,
        totalArticles: summary.totalArticles,
        articles: articles.map(a => ({
          title: a.title,
          source: a.source,
          url: a.url
        }))
      });
    } catch (error) {
      console.error('[ERROR] Search and Summarize Error:', error.message);
      console.error('[ERROR] Stack:', error.stack);
      
      res.status(500).json({ 
        error: 'Failed to search and summarize',
        details: error.response?.data?.error || error.message 
      });
    }
  }

  async scrapeAndSummarize(req, res) {
    try {
      const { urls, query } = req.body;
      
      if (!urls || !Array.isArray(urls) || urls.length === 0) {
        return res.status(400).json({ error: 'URLs array is required' });
      }

      // 1. Scrape tất cả URLs bằng Puppeteer (GIỚI HẠN 3 LUỔNG)
      console.log(`[PUPPETEER] Scraping ${urls.length} articles (concurrency: 3)...`);
      const scrapePromises = urls.map((url, index) => 
        scrapeLimit(async () => {
          try {
            const scraped = await scrapeService.scrapeUrl(url);
            console.log(`[PUPPETEER] Successfully scraped: ${url}`);
            return {
              title: scraped.title || `Bai ${index + 1}`,
              source: new URL(url).hostname,
              content: scraped.text || '',
              url: url
            };
          } catch (err) {
            console.error(`[PUPPETEER] Failed to scrape ${url}:`, err.message);
            return null;
          }
        })
      );

      const articles = (await Promise.all(scrapePromises)).filter(a => a !== null);
      console.log(`[PUPPETEER] Successfully scraped ${articles.length}/${urls.length} articles`);

      if (articles.length === 0) {
        return res.status(500).json({ error: 'Khong the scrape duoc bai bao nao' });
      }

      // 2. Gửi tất cả vào Gemini để tóm tắt
      console.log(`[GEMINI API] Starting summarization of ${articles.length} articles...`);
      let summary;
      try {
        summary = await geminiService.summarizeMultipleNews(articles, query || '');
        console.log('[GEMINI API] Summarization successful');
      } catch (err) {
        console.error('[GEMINI API] ERROR:', err.message);
        console.error('[GEMINI API] Status:', err.response?.status);
        console.error('[GEMINI API] Details:', err.response?.data);
        
        if (err.message.includes('PROHIBITED_CONTENT')) {
          return res.status(400).json({ 
            error: 'Prohibited content',
            api: 'Google Gemini API',
            details: 'Nội dung không phù hợp. Gemini AI đã chặn nội dung này vì vi phạm tiêu chuẩn an toàn.'
          });
        }
        
        if (err.response?.status === 429 || err.message.includes('429')) {
          return res.status(429).json({ 
            error: 'Rate limit exceeded',
            api: 'Google Gemini API',
            details: 'Vuot qua gioi han API Gemini. Vui long thu lai sau it phut.' 
          });
        }
        throw err;
      }

      console.log('[SUCCESS] Scrape and summarize completed successfully');
      res.json({
        summary: summary.summary,
        totalArticles: summary.totalArticles
      });
    } catch (error) {
      console.error('[ERROR] Scrape and Summarize Error:', error.message);
      console.error('[ERROR] Stack:', error.stack);
      
      res.status(500).json({ 
        error: 'Failed to scrape and summarize',
        details: error.message 
      });
    }
  }
}

export default new SearchController();
