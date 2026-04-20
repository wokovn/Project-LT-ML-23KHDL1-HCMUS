import { randomUUID } from 'crypto';
import { createClient } from '@supabase/supabase-js';
import supabaseConfig from '../config/supabase.config.js';
import audioTranscodeService from './audioTranscode.service.js';
import ttsService from './tts.service.js';

const MAX_JOBS = 300;

class TtsJobService {
  constructor() {
    this.jobs = new Map();
    this.supabase = null;

    if (supabaseConfig.URL && supabaseConfig.KEY) {
      this.supabase = createClient(supabaseConfig.URL, supabaseConfig.KEY);
    }
  }

  createJob(payload) {
    const key = randomUUID();
    const now = new Date().toISOString();

    const job = {
      key,
      status: 'queued',
      createdAt: now,
      updatedAt: now,
      error: null,
      audioUrl: null
    };

    this.jobs.set(key, job);
    this.trimJobs();

    this.processJob(key, payload).catch((error) => {
      this.updateJob(key, {
        status: 'failed',
        error: error.message || 'Unknown error'
      });
    });

    return {
      key,
      status: 'queued',
      createdAt: now
    };
  }

  getJob(key) {
    return this.jobs.get(key) || null;
  }

  updateJob(key, patch) {
    const existing = this.jobs.get(key);
    if (!existing) return;

    this.jobs.set(key, {
      ...existing,
      ...patch,
      updatedAt: new Date().toISOString()
    });
  }

  trimJobs() {
    if (this.jobs.size <= MAX_JOBS) return;

    const removableCount = this.jobs.size - MAX_JOBS;
    const keys = [...this.jobs.keys()].slice(0, removableCount);
    keys.forEach((key) => this.jobs.delete(key));
  }

  async uploadAudio({ key, fileBuffer, format }) {
    if (!this.supabase) {
      throw new Error('Supabase is not configured. Please set SUPABASE_URL and SUPABASE_KEY');
    }

    const objectPath = `${key}.${format}`;
    const contentType = format === 'mp3' ? 'audio/mpeg' : 'audio/wav';

    const { error: uploadError } = await this.supabase.storage
      .from(supabaseConfig.TTS_BUCKET)
      .upload(objectPath, fileBuffer, {
        contentType,
        upsert: true,
        cacheControl: '31536000'
      });

    if (uploadError) {
      throw new Error(`Supabase upload failed: ${uploadError.message}`);
    }

    const publicResult = this.supabase.storage
      .from(supabaseConfig.TTS_BUCKET)
      .getPublicUrl(objectPath);

    let audioUrl = publicResult?.data?.publicUrl || null;

    if (!audioUrl) {
      const signedResult = await this.supabase.storage
        .from(supabaseConfig.TTS_BUCKET)
        .createSignedUrl(objectPath, 60 * 60 * 24 * 7);

      if (signedResult.error) {
        throw new Error(`Supabase signed URL failed: ${signedResult.error.message}`);
      }

      audioUrl = signedResult.data.signedUrl;
    }

    return { audioUrl };
  }

  async processJob(key, payload) {
    this.updateJob(key, {
      status: 'processing',
      error: null
    });

    const synthData = await ttsService.synthesize(payload);

    if (!synthData?.audio_base64) {
      throw new Error('FastAPI did not return audio data');
    }

    const wavBuffer = Buffer.from(synthData.audio_base64, 'base64');
    const uploadBuffer = await audioTranscodeService.convertWavToMp3(wavBuffer);
    const format = 'mp3';

    const uploadResult = await this.uploadAudio({
      key,
      fileBuffer: uploadBuffer,
      format
    });

    this.updateJob(key, {
      status: 'completed',
      error: null,
      audioUrl: uploadResult.audioUrl
    });
  }
}

export default new TtsJobService();
