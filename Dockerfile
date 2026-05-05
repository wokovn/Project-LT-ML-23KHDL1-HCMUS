# --- Stage 1: Build Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
ENV VITE_API_URL=/api
RUN npm run build

# --- Stage 2: Final Image ---
FROM node:20-slim

# Install system dependencies
# Includes dependencies for: Nginx, Puppeteer, and Python C-extensions
RUN apt-get update && apt-get install -y \
    curl \
    nginx \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    wget \
    gnupg \
    ca-certificates \
    procps \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    fonts-liberation \
    lsb-release \
    xdg-utils \
    ffmpeg \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Backend and install dependencies
COPY backend/package*.json ./backend/
RUN cd backend && npm install

# Install minimal Python dependencies for scraping (if needed)
# We exclude the heavy XTTS/ML dependencies
COPY requirements.txt ./
RUN sed -i '/-r/d' requirements.txt && \
    pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy all code
COPY . .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Setup Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 7860 for Hugging Face
EXPOSE 7860

# Ensure start.sh is executable
RUN chmod +x /app/start.sh

# Start all services via start.sh
CMD ["/app/start.sh"]
