import express from 'express';
import ttsController from '../controllers/tts.controller.js';

const router = express.Router();

router.get('/tts/health', ttsController.health.bind(ttsController));
router.post('/tts/synthesize', ttsController.synthesize.bind(ttsController));
router.post('/tts/tasks', ttsController.createTask.bind(ttsController));
router.get('/tts/tasks/:taskId', ttsController.getTask.bind(ttsController));
router.post('/tts/jobs', ttsController.createStorageJob.bind(ttsController));
router.get('/tts/jobs/:key', ttsController.getStorageJob.bind(ttsController));

export default router;
