import scrapeService from '../services/scrape.service.js';

class ScrapeController {
  async scrape(req, res) {
    try {
      const { url } = req.body;
      
      if (!url) {
        return res.status(400).json({ error: 'URL is required' });
      }

      const data = await scrapeService.scrapeUrl(url);
      res.json(data);
    } catch (error) {
      console.error('Scrape Error:', error.message);
      res.status(500).json({ 
        error: 'Failed to scrape URL',
        details: error.message 
      });
    }
  }
}

export default new ScrapeController();
