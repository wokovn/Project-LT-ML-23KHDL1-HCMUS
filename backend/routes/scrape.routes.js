import express from 'express';
import scrapeController from '../controllers/scrape.controller.js';

const router = express.Router();

router.post('/scrape', scrapeController.scrape.bind(scrapeController));

export default router;
