import ttsService from '../services/tts.service.js';
import ttsJobService from '../services/ttsJob.service.js';
import audioTranscodeService from '../services/audioTranscode.service.js';

class TtsController {
  handleServiceError(error, res, defaultMessage) {
    console.error('[TTS Bridge] Error:', error.message);

    if (error.response) {
      return res.status(error.response.status).json({
        error: defaultMessage,
        details: error.response.data
      });
    }

    return res.status(500).json({
      error: defaultMessage,
      details: error.message
    });
  }

  async health(req, res) {
    try {
      const data = await ttsService.health();
      return res.json(data);
    } catch (error) {
      return this.handleServiceError(error, res, 'Failed to reach TTS service');
    }
  }

  async synthesize(req, res) {
    try {
      const { text, language, speaker_audio } = req.body;

      if (!text) {
        return res.status(400).json({ error: 'Text is required' });
      }

      const data = await ttsService.synthesize({
        text,
        language,
        speaker_audio
      });

      if (!data?.audio_base64) {
        return res.status(502).json({ error: 'TTS service returned empty audio payload' });
      }

      const wavBuffer = Buffer.from(data.audio_base64, 'base64');
      const mp3Buffer = await audioTranscodeService.convertWavToMp3(wavBuffer);

      const responsePayload = {
        ...data,
        audio_base64: mp3Buffer.toString('base64'),
        format: 'mp3',
        mime_type: 'audio/mpeg',
        size_bytes: mp3Buffer.length
      };

      return res.json(responsePayload);
    } catch (error) {
      return this.handleServiceError(error, res, 'Failed to synthesize speech');
    }
  }

  async createTask(req, res) {
    try {
      const { text, language, speaker_audio } = req.body;

      if (!text) {
        return res.status(400).json({ error: 'Text is required' });
      }

      const data = await ttsService.createTask({
        text,
        language,
        speaker_audio
      });

      return res.status(202).json(data);
    } catch (error) {
      return this.handleServiceError(error, res, 'Failed to dispatch TTS task');
    }
  }

  async getTask(req, res) {
    try {
      const { taskId } = req.params;

      if (!taskId) {
        return res.status(400).json({ error: 'taskId is required' });
      }

      const data = await ttsService.getTask(taskId);
      return res.json(data);
    } catch (error) {
      return this.handleServiceError(error, res, 'Failed to fetch TTS task status');
    }
  }

  async createStorageJob(req, res) {
    try {
      const { text, language, speaker_audio } = req.body;

      if (!text) {
        return res.status(400).json({ error: 'Text is required' });
      }

      const data = ttsJobService.createJob({
        text,
        language,
        speaker_audio
      });

      return res.status(202).json(data);
    } catch (error) {
      return this.handleServiceError(error, res, 'Failed to create TTS storage job');
    }
  }

  async getStorageJob(req, res) {
    try {
      const { key } = req.params;

      if (!key) {
        return res.status(400).json({ error: 'key is required' });
      }

      const data = ttsJobService.getJob(key);

      if (!data) {
        return res.status(404).json({ error: 'TTS job not found' });
      }

      return res.json(data);
    } catch (error) {
      return this.handleServiceError(error, res, 'Failed to fetch TTS storage job');
    }
  }
}

export default new TtsController();
