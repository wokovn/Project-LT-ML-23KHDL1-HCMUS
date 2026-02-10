import express from 'express';
import searchRoutes from './search.routes.js';
import scrapeRoutes from './scrape.routes.js';
import geminiRoutes from './gemini.routes.js';

const router = express.Router();

// Health check
router.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'Server is running' });
});

// Mount routes
router.use('/', searchRoutes);
router.use('/', scrapeRoutes);
router.use('/', geminiRoutes);

export default router;
