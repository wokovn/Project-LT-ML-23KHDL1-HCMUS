import puppeteer from 'puppeteer';
import puppeteerConfig from '../config/puppeteer.config.js';

class ScrapeService {
  async scrapeUrl(url) {
    let browser = null;
    try {
      browser = await puppeteer.launch({
        headless: puppeteerConfig.HEADLESS,
        args: [
          ...puppeteerConfig.ARGS,
          '--disable-blink-features=AutomationControlled'
        ]
      });
      
      const page = await browser.newPage();
      
      // Set user agent để giả lập Chrome thật
      await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
      
      // Set viewport
      await page.setViewport({ width: 1920, height: 1080 });
      
      // Disable images và CSS để tải nhanh hơn
      await page.setRequestInterception(true);
      page.on('request', (req) => {
        if (['image', 'stylesheet', 'font'].includes(req.resourceType())) {
          req.abort();
        } else {
          req.continue();
        }
      });
      
      // Override webdriver property
      await page.evaluateOnNewDocument(() => {
        Object.defineProperty(navigator, 'webdriver', {
          get: () => false
        });
      });
      
      // Navigate với multiple strategies
      try {
        await page.goto(url, { 
          waitUntil: 'domcontentloaded',
          timeout: 45000
        });
      } catch (err) {
        // Fallback: try with networkidle0
        console.log(`[PUPPETEER] Retrying ${url} with networkidle0...`);
        await page.goto(url, { 
          waitUntil: 'networkidle0',
          timeout: 30000
        });
      }
      
      // Wait for dynamic content using Promise-based delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const data = await page.evaluate(() => {
        // Try to find main content
        const articleSelectors = [
          'article',
          '[class*="article"]',
          '[class*="content"]',
          '[class*="post"]',
          'main',
          '.entry-content',
          '#content'
        ];
        
        let text = '';
        let foundSelector = 'none';
        for (const selector of articleSelectors) {
          const element = document.querySelector(selector);
          if (element && element.innerText.length > 200) {
            text = element.innerText;
            foundSelector = selector;
            break;
          }
        }
        
        // Fallback to body
        if (!text) {
          text = document.body.innerText;
          foundSelector = 'body';
        }
        
        return {
          title: document.title,
          url: window.location.href,
          text: text.substring(0, 2000),
          selector: foundSelector,
          textLength: text.length
        };
      });

      console.log(`[PUPPETEER] Scraped from selector: ${data.selector}, length: ${data.textLength}`);
      console.log(`[PUPPETEER] Content preview: ${data.text.substring(0, 200)}...`);

      return data;
    } finally {
      if (browser) {
        await browser.close();
      }
    }
  }
}

export default new ScrapeService();
