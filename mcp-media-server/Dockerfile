FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# ffmpeg is required for audio processing
# curl/wget might be needed for debugging
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create temp directories
RUN mkdir -p temp_downloads

COPY . .

CMD ["fastmcp", "run", "src/server.py", "--transport", "sse", "--port", "7860", "--host", "0.0.0.0"]
