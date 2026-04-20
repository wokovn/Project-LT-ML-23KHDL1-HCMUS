import { spawn } from 'child_process';
import ffmpegStaticPath from 'ffmpeg-static';

const DEFAULT_MP3_BITRATE = process.env.TTS_MP3_BITRATE || '64k';

class AudioTranscodeService {
  constructor() {
    this.ffmpegCommand = ffmpegStaticPath || process.env.FFMPEG_PATH || 'ffmpeg';
  }

  async convertWavToMp3(wavBuffer) {
    if (!wavBuffer || wavBuffer.length === 0) {
      throw new Error('WAV buffer is empty');
    }

    return new Promise((resolve, reject) => {
      const ffmpeg = spawn(this.ffmpegCommand, [
        '-hide_banner',
        '-loglevel',
        'error',
        '-f',
        'wav',
        '-i',
        'pipe:0',
        '-vn',
        '-codec:a',
        'libmp3lame',
        '-b:a',
        DEFAULT_MP3_BITRATE,
        '-f',
        'mp3',
        'pipe:1'
      ]);

      const outputChunks = [];
      const errorChunks = [];

      ffmpeg.stdout.on('data', (chunk) => outputChunks.push(chunk));
      ffmpeg.stderr.on('data', (chunk) => errorChunks.push(chunk));

      ffmpeg.on('error', (error) => {
        reject(
          new Error(
            `Cannot run ffmpeg command "${this.ffmpegCommand}": ${error.message}`
          )
        );
      });

      ffmpeg.on('close', (code) => {
        if (code !== 0) {
          const stderr = Buffer.concat(errorChunks).toString('utf8').trim();
          reject(new Error(stderr || `ffmpeg exited with code ${code}`));
          return;
        }

        const mp3Buffer = Buffer.concat(outputChunks);
        if (!mp3Buffer.length) {
          reject(new Error('ffmpeg produced an empty MP3 output'));
          return;
        }

        resolve(mp3Buffer);
      });

      ffmpeg.stdin.write(wavBuffer);
      ffmpeg.stdin.end();
    });
  }
}

export default new AudioTranscodeService();
