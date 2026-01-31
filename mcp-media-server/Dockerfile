FROM python:3.10-slim

# Install system dependencies
# ffmpeg is required for whisper and audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 user

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY local_media_server.py .

# Change ownership to non-root user
RUN chown -R user:user /app

# Switch to non-root user
USER user

# Set environment variables
ENV PATH="/home/user/.local/bin:$PATH"

# Expose port 7860 for Hugging Face Spaces
EXPOSE 7860

# Run the server
CMD ["fastmcp", "run", "local_media_server.py", "--transport", "sse", "--port", "7860", "--host", "0.0.0.0"]
