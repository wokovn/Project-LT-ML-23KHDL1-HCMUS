# Project-LT-ML-23KHDL1-HCMUS

A full-stack web application built with React, Express.js, and integrated with multiple APIs including Brave Search, Puppeteer, and Google Gemini AI.

## Features

- **React Frontend** with modern CSS styling
- **Express.js Backend** with RESTful API endpoints
- **Brave Search API** integration for web search
- **Puppeteer** for web scraping
- **Google Gemini AI** for AI-powered content generation
- **vnTTS GPU FastAPI** service for Vietnamese text-to-speech

## Project Structure

```
.
├── backend/          # Express.js server
│   ├── server.js     # Main server file
│   ├── package.json
│   ├── .env.example  # Environment variables template
│   └── tts_fastapi/  # Python FastAPI service for vnTTS
├── frontend/         # React application
│   ├── src/
│   │   ├── App.jsx   # Main React component
│   │   ├── App.css   # Styling
│   │   └── ...
│   ├── package.json
│   └── .env.example  # Environment variables template
└── README.md
```

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Python 3.11 (recommended for XTTS/vnTTS inference)
- NVIDIA GPU + CUDA-compatible driver (for GPU inference)
- Brave Search API key
- Google Gemini API key

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/wokovn/Project-LT-ML-23KHDL1-HCMUS.git
cd Project-LT-ML-23KHDL1-HCMUS
```

### 2. Backend Setup

```bash
cd backend
npm install

# Create .env file from example
cp .env.example .env

# Edit .env and add your API keys:
# BRAVE_API_KEY=your_brave_api_key_here
# GEMINI_API_KEY=your_gemini_api_key_here
# PORT=5000
# TTS_SERVICE_URL=http://127.0.0.1:8001
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your_supabase_service_role_or_secret_key
# SUPABASE_TTS_BUCKET=tts_audio
```

### 2.5 vnTTS FastAPI (GPU) Setup

Run from project root:

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv311\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
.\.venv311\Scripts\python.exe -m pip install -r .\models\XTTSv2-Finetuning-for-New-Languages\requirements.txt
.\.venv311\Scripts\python.exe -m pip install -r .\backend\tts_fastapi\requirements.txt
.\.venv311\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='anhnh2002/vnTTS', repo_type='model', local_dir='models/vntts-runtime-model')"
```

Start FastAPI service:

```powershell
$env:PYTHONPATH="e:/Users/Admin/Documents/GitHub/Project-LT-ML-23KHDL1-HCMUS/models/XTTSv2-Finetuning-for-New-Languages"
$env:VNTTS_MODEL_DIR="e:/Users/Admin/Documents/GitHub/Project-LT-ML-23KHDL1-HCMUS/models/vntts-runtime-model"
$env:VNTTS_DEVICE="cuda:0"
.\.venv311\Scripts\python.exe -m uvicorn backend.tts_fastapi.app:app --host 127.0.0.1 --port 8001
```

### 3. Frontend Setup

```bash
cd ../frontend
npm install

# Create .env file from example
cp .env.example .env

# Edit .env and set API URL (default is http://localhost:5000):
# VITE_API_URL=http://localhost:5000
```

### 4. Getting API Keys

#### Brave Search API
1. Visit [Brave Search API](https://brave.com/search/api/)
2. Sign up for an API key
3. Add the key to `backend/.env` as `BRAVE_API_KEY`

#### Google Gemini API
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Add the key to `backend/.env` as `GEMINI_API_KEY`

## Running the Application

### Quickstart (Dev/Start)

From project root, run one file for all services (FastAPI + backend + frontend):

```powershell
# Dev mode: backend nodemon + frontend vite dev
.\quickstart.ps1 -Mode dev

# Start mode: backend start + frontend build/preview
.\quickstart.ps1 -Mode start
```

Preview commands only (without launching terminals):

```powershell
.\quickstart.ps1 -Mode dev -DryRun
```

### Start Backend Server

```bash
cd backend
npm start
```

The backend server will run on `http://localhost:5000`

### Start Frontend Development Server

In a new terminal:

```bash
cd frontend
npm run dev
```

The frontend will run on `http://localhost:5173`

## API Endpoints

### Backend API

- `GET /api/health` - Health check endpoint
- `POST /api/search` - Brave Search API
  - Body: `{ "query": "search term" }`
- `POST /api/scrape` - Puppeteer web scraping
  - Body: `{ "url": "https://example.com" }`
- `POST /api/gemini` - Gemini AI content generation
  - Body: `{ "prompt": "your prompt here" }`
- `GET /api/tts/health` - FastAPI vnTTS health check
- `POST /api/tts/synthesize` - Sync TTS inference
  - Body: `{ "text": "xin chao", "language": "vi", "speaker_audio": "vi_man.wav" }`
  - Output audio luôn được trả về dạng MP3 (base64)
- `POST /api/tts/tasks` - Async TTS task dispatch
  - Body: `{ "text": "xin chao" }`
- `GET /api/tts/tasks/:taskId` - Poll async TTS task result
- `POST /api/tts/jobs` - Create UUID-based TTS storage job
  - Body: `{ "text": "xin chao" }`
  - Response: `{ "key": "uuid", "status": "queued", "createdAt": "..." }`
- `GET /api/tts/jobs/:key` - Poll UUID-based TTS storage job
  - Returns status (`queued|processing|completed|failed`) and `audioUrl` when done

## Supabase Notes For TTS Jobs

- Bucket mặc định là `tts_audio` (có thể đổi bằng `SUPABASE_TTS_BUCKET`).
- Khi có `SUPABASE_URL` + `SUPABASE_KEY`, backend sẽ upload audio lên bucket và trả `audioUrl`.
- Backend ép chuyển WAV sang MP3 bằng ffmpeg trước khi trả kết quả hoặc upload.
- Không dùng bảng Supabase/Postgres cho lịch sử TTS; frontend tự lưu lịch sử local.

## Usage

1. Open your browser and navigate to `http://localhost:5173`
2. Use the tabs to switch between different features:
   - **Brave Search**: Search the web using Brave Search API
   - **Puppeteer Scraper**: Scrape content from any website
   - **Gemini AI**: Generate content using Google's Gemini AI

## Technologies Used

### Frontend
- React 18
- Vite
- Axios
- CSS3

### Backend
- Express.js
- Puppeteer
- Google Generative AI SDK
- Axios
- CORS
- dotenv

## License

ISC

## Contributing

Feel free to submit issues and pull requests.
