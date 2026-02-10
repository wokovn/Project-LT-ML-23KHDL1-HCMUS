import puppeteer from 'puppeteer';
import puppeteerConfig from '../config/puppeteer.config.js';
import fs from 'fs';
import os from 'os';
import path from 'path';

class ScrapeService {
  async scrapeUrl(url) {
    let browser = null;
    let tempDir = null;
    
    try {
      // Tạo thư mục tạm rieng biệt cho mỗi instance (FIX EBUSY)
      tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'puppeteer-'));
      console.log(`[PUPPETEER] Using temp dir: ${tempDir}`);
      
      browser = await puppeteer.launch({
        headless: puppeteerConfig.HEADLESS,
        userDataDir: tempDir, // Mỗi instance có userDataDir riêng
        args: [
          ...puppeteerConfig.ARGS,
          '--disable-blink-features=AutomationControlled',
          '--disable-dev-shm-usage', // Giảm memory usage
          '--no-first-run',
          '--no-default-browser-check'
        ]
      });
      
      const page = await browser.newPage();
      
      // Set user agent để giả lập Chrome thật
      await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
      
      // Set viewport
      await page.setViewport({ width: 1920, height: 1080 });
      
      // Set extra headers
      await page.setExtraHTTPHeaders({
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
      });
      
      // Disable images và CSS để tải nhanh hơn (REQUEST INTERCEPTION)
      await page.setRequestInterception(true);
      page.on('request', (req) => {
        const resourceType = req.resourceType();
        if (['image', 'stylesheet', 'font', 'media'].includes(resourceType)) {
          req.abort();
        } else {
          req.continue();
        }
      });
      
      // Override webdriver property (STEALTH MODE)
      await page.evaluateOnNewDocument(() => {
        Object.defineProperty(navigator, 'webdriver', {
          get: () => false
        });
        
        // Override chrome property
        window.chrome = {
          runtime: {}
        };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
          parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );
      });
      
      // Navigate với optimized strategy (CHI DÙNG DOMCONTENTLOADED)
      console.log(`[NAV] Đang vào: ${url} (Timeout: 60s)`);
      
      try {
        await page.goto(url, { 
          waitUntil: 'domcontentloaded', // Chỉ chờ HTML, không chờ quảng cáo/video
          timeout: 60000 // Tăng lên 60s
        });
        
        // Special handling cho YouTube/Reddit/TikTok - chờ thêm 2s
        const heavySites = ['youtube', 'reddit', 'tiktok', 'facebook', 'twitter'];
        if (heavySites.some(site => url.includes(site))) {
          console.log(`[NAV] Heavy site detected, waiting extra 2s...`);
          await new Promise(r => setTimeout(r, 2000));
        }
        
        console.log(`[SUCCESS] ✅ Đã tải: ${url.substring(0, 50)}...`);
      } catch (err) {
        console.error(`[FAIL] ❌ Timeout: ${url}`);
        throw err;
      }
      
      // Wait for dynamic content (1s thôi, không cần lâu)
      await new Promise(resolve => setTimeout(resolve, 1000));
      
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
    } catch (error) {
      console.error(`[PUPPETEER] Error scraping ${url}:`, error.message);
      throw error;
    } finally {
      // Cleanup
      if (browser) {
        await browser.close();
        // Chờ 1s cho browser đóng hẳn trước khi xóa folder (FIX EPERM)
        await new Promise(r => setTimeout(r, 1000));
      }
      
      // Xóa thư mục tạm (FIX EBUSY)
      if (tempDir) {
        try {
          fs.rmSync(tempDir, { recursive: true, force: true });
          console.log(`[PUPPETEER] Cleaned up temp dir: ${tempDir}`);
        } catch (cleanupErr) {
          console.warn(`[PUPPETEER] Thôi kệ, dọn sau cũng được: ${cleanupErr.message}`);
        }
      }
    }
  }
}

export default new ScrapeService();
