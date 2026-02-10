import express from 'express';
import geminiController from '../controllers/gemini.controller.js';

const router = express.Router();

router.post('/gemini', geminiController.generate.bind(geminiController));
router.post('/gemini/summarize', geminiController.summarize.bind(geminiController));

export default router;
