# Project-LT-ML-23KHDL1-HCMUS

A full-stack web application built with React, Express.js, and integrated with multiple APIs including Brave Search, Puppeteer, and Google Gemini AI.

## Features

- **React Frontend** with modern CSS styling
- **Express.js Backend** with RESTful API endpoints
- **Brave Search API** integration for web search
- **Puppeteer** for web scraping
- **Google Gemini AI** for AI-powered content generation

## Project Structure

```
.
├── backend/          # Express.js server
│   ├── server.js     # Main server file
│   ├── package.json
│   └── .env.example  # Environment variables template
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
- Brave Search API key
- Google Gemini API key

## Setup Instructions

### 1. Clone the repository

```bash
git clone <repository-url>
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