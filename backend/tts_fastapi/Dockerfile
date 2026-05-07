FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root and subdirs as needed
COPY requirements.txt ./
COPY backend/tts_fastapi/requirements.txt ./backend/tts_fastapi/
COPY models/XTTSv2-Finetuning-for-New-Languages/requirements.txt ./models/XTTSv2-Finetuning-for-New-Languages/

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/backend/tts_fastapi
EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
