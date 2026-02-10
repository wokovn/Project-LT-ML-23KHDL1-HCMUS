require('dotenv').config();
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const puppeteer = require('puppeteer');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize Gemini AI
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// Health check route
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Server is running' });
});

// Brave Search API endpoint
app.post('/api/search', async (req, res) => {
  try {
    const { query } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Query is required' });
    }

    if (!process.env.BRAVE_API_KEY) {
      return res.status(500).json({ error: 'Brave API key not configured' });
    }

    const response = await axios.get('https://api.search.brave.com/res/v1/web/search', {
      params: { q: query },
      headers: {
        'Accept': 'application/json',
        'X-Subscription-Token': process.env.BRAVE_API_KEY
      }
    });

    res.json(response.data);
  } catch (error) {
    console.error('Brave Search Error:', error.message);
    res.status(500).json({ 
      error: 'Failed to perform search',
      details: error.response?.data || error.message 
    });
  }
});

// Puppeteer scraping endpoint
app.post('/api/scrape', async (req, res) => {
  let browser = null;
  try {
    const { url } = req.body;
    
    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }

    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    
    const data = await page.evaluate(() => {
      return {
        title: document.title,
        url: window.location.href,
        text: document.body.innerText.substring(0, 1000)
      };
    });

    await browser.close();
    res.json(data);
  } catch (error) {
    if (browser) {
      await browser.close();
    }
    console.error('Puppeteer Error:', error.message);
    res.status(500).json({ 
      error: 'Failed to scrape URL',
      details: error.message 
    });
  }
});

// Gemini AI endpoint
app.post('/api/gemini', async (req, res) => {
  try {
    const { prompt } = req.body;
    
    if (!prompt) {
      return res.status(400).json({ error: 'Prompt is required' });
    }

    if (!process.env.GEMINI_API_KEY) {
      return res.status(500).json({ error: 'Gemini API key not configured' });
    }

    const model = genAI.getGenerativeModel({ model: 'gemini-pro' });
    const result = await model.generateContent(prompt);
    const response = await result.response;
    const text = response.text();

    res.json({ text });
  } catch (error) {
    console.error('Gemini AI Error:', error.message);
    res.status(500).json({ 
      error: 'Failed to generate content',
      details: error.message 
    });
  }
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
