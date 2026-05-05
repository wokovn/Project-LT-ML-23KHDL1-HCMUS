import axios from 'axios';
import * as cheerio from 'cheerio';
import puppeteer from 'puppeteer';
import puppeteerConfig from '../config/puppeteer.config.js';
import fs from 'fs';
import os from 'os';
import path from 'path';

// ─── Shared browser-like headers ──────────────────────────────────────────────
const BROWSER_HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  'Accept':
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
  'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
  'Accept-Encoding': 'gzip, deflate, br',
  'Cache-Control': 'no-cache',
  'Pragma': 'no-cache',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'none',
  'Upgrade-Insecure-Requests': '1',
};

// ─── Content selectors (ordered by priority) ──────────────────────────────────
const ARTICLE_SELECTORS = [
  'article',
  '[class*="article-body"]',
  '[class*="article-content"]',
  '[class*="post-content"]',
  '[class*="entry-content"]',
  '[itemprop="articleBody"]',
  '.content-detail',   // VnExpress
  '.fck_detail',       // VnExpress
  '#main-detail-body', // Tuổi Trẻ
  '.detail-content',   // Thanh Niên
  '.singular-content', // Dân Trí
  'main',
  '#content',
  '.content',
];

// ─── Fast scrape via axios + cheerio ──────────────────────────────────────────
async function scrapeWithAxios(url) {
  const t0 = Date.now();
  const shortUrl = url.substring(0, 60);
  console.log(`[AXIOS] ⏳ Fetching: ${shortUrl}`);

  const response = await axios.get(url, {
    headers: { ...BROWSER_HEADERS, Referer: new URL(url).origin },
    timeout: 8000,        // 8s hard limit
    maxRedirects: 5,
    responseType: 'arraybuffer', // handle encoding correctly
  });
  console.log(`[AXIOS] ✅ Got HTTP ${response.status} in ${Date.now() - t0}ms — ${shortUrl}`);

  // Detect charset from Content-Type header
  const contentType = response.headers['content-type'] || '';
  const charsetMatch = contentType.match(/charset=([^\s;]+)/i);
  const charset = charsetMatch ? charsetMatch[1].toLowerCase() : 'utf-8';

  let html;
  try {
    html = new TextDecoder(charset).decode(response.data);
  } catch {
    html = new TextDecoder('utf-8').decode(response.data);
  }

  const t1 = Date.now();
  const $ = cheerio.load(html);

  // Remove noise elements
  $('script, style, noscript, nav, header, footer, aside, [class*="ads"], [class*="banner"], [id*="ads"], [class*="related"], [class*="comment"]').remove();

  const title = $('title').text().trim() || $('h1').first().text().trim() || '';

  // Try selectors in order
  let text = '';
  let foundSelector = 'none';
  for (const sel of ARTICLE_SELECTORS) {
    const el = $(sel).first();
    const content = el.text().replace(/\s+/g, ' ').trim();
    if (content.length > 300) {
      text = content;
      foundSelector = sel;
      break;
    }
  }

  // Fallback: body text
  if (!text) {
    text = $('body').text().replace(/\s+/g, ' ').trim();
    foundSelector = 'body';
  }

  console.log(`[AXIOS] 📄 selector="${foundSelector}" chars=${text.length} parse=${Date.now()-t1}ms total=${Date.now()-t0}ms — ${shortUrl}`);

  return {
    title,
    url,
    text: text.substring(0, 3000),
    selector: foundSelector,
    textLength: text.length,
  };
}

// ─── Slow scrape via Puppeteer (fallback) ─────────────────────────────────────
async function scrapeWithPuppeteer(url) {
  let browser = null;
  let tempDir = null;
  const t0 = Date.now();
  const shortUrl = url.substring(0, 60);

  try {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'puppeteer-'));
    console.log(`[PUPPETEER] 🚀 Launching browser for: ${shortUrl}`);

    browser = await puppeteer.launch({
      headless: puppeteerConfig.HEADLESS,
      userDataDir: tempDir,
      args: [
        ...puppeteerConfig.ARGS,
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-first-run',
        '--no-default-browser-check',
      ],
    });

    const page = await browser.newPage();
    await page.setUserAgent(BROWSER_HEADERS['User-Agent']);
    await page.setViewport({ width: 1920, height: 1080 });
    await page.setExtraHTTPHeaders({
      'Accept-Language': BROWSER_HEADERS['Accept-Language'],
      Accept: BROWSER_HEADERS['Accept'],
    });

    // Block heavy assets
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      const t = req.resourceType();
      if (['image', 'stylesheet', 'font', 'media'].includes(t)) {
        req.abort();
      } else {
        req.continue();
      }
    });

    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => false });
      window.chrome = { runtime: {} };
    });

    const tNav = Date.now();
    console.log(`[PUPPETEER] ⏳ Navigating (browser launch took ${tNav - t0}ms)...`);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 25000 });
    console.log(`[PUPPETEER] ✅ DOM loaded in ${Date.now() - tNav}ms — ${shortUrl}`);
    await new Promise((r) => setTimeout(r, 800));

    const data = await page.evaluate((selectors) => {
      const removeEls = document.querySelectorAll(
        'script,style,noscript,nav,header,footer,aside'
      );
      removeEls.forEach((el) => el.remove());

      const title =
        document.title ||
        document.querySelector('h1')?.innerText ||
        '';
      let text = '';
      let foundSelector = 'none';

      for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el && (el.innerText || '').length > 300) {
          text = el.innerText;
          foundSelector = sel;
          break;
        }
      }

      if (!text) {
        text = document.body?.innerText || '';
        foundSelector = 'body';
      }

      return {
        title: title.trim(),
        url: window.location.href,
        text: text.replace(/\s+/g, ' ').trim().substring(0, 3000),
        selector: foundSelector,
        textLength: text.length,
      };
    }, ARTICLE_SELECTORS);

    console.log(`[PUPPETEER] 📄 selector="${data.selector}" chars=${data.textLength} total=${Date.now()-t0}ms — ${shortUrl}`);
    return data;
  } finally {
    if (browser) {
      await browser.close();
      await new Promise((r) => setTimeout(r, 500));
    }
    if (tempDir) {
      try {
        fs.rmSync(tempDir, { recursive: true, force: true });
      } catch {
        // ignore cleanup errors
      }
    }
  }
}

const IS_PRODUCTION = process.env.NODE_ENV === 'production';

// ─── Public API ───────────────────────────────────────────────────────────────
class ScrapeService {
  /**
   * Production: axios+cheerio only (Puppeteer uses 150-300MB RAM per instance
   * which OOM-kills the process on Render's 512MB free tier).
   * Development: axios first, Puppeteer fallback if content is thin/blocked.
   */
  async scrapeUrl(url) {
    try {
      const data = await scrapeWithAxios(url);

      if (data.textLength >= 300) {
        return data;
      }

      // axios returned thin content
      if (IS_PRODUCTION) {
        console.warn(`[SCRAPE] axios thin content (${data.textLength} chars) — returning as-is (Puppeteer disabled in production)`);
        return data; // return what we have; don't risk OOM
      }

      console.warn(`[SCRAPE] axios thin content (${data.textLength} chars) — falling back to Puppeteer`);
    } catch (err) {
      const status = err.response?.status;
      const msg = `${status || err.message}`;

      if (IS_PRODUCTION) {
        console.warn(`[SCRAPE] axios failed (${msg}) — skipping Puppeteer in production, returning empty`);
        // Return empty stub so the slot is skipped downstream
        throw err;
      }

      console.warn(`[SCRAPE] axios failed (${msg}) — falling back to Puppeteer`);
    }

    // Development fallback only
    return scrapeWithPuppeteer(url);
  }
}

export default new ScrapeService();

