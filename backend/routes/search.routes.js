import express from 'express';
import searchController from '../controllers/search.controller.js';

const router = express.Router();

router.post('/search', searchController.search.bind(searchController));
router.post('/search-summarize', searchController.searchAndSummarize.bind(searchController));
router.post('/scrape-summarize', searchController.scrapeAndSummarize.bind(searchController));

export default router;
