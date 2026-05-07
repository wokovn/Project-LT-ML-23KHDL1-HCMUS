export default {
  SERVICE_URL: process.env.TTS_SERVICE_URL || 'http://127.0.0.1:8001',
  TIMEOUT_MS: Number(process.env.TTS_SERVICE_TIMEOUT_MS || 600000)
};
