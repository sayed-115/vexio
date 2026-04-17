FROM python:3.11-slim

# Install ffmpeg which is strictly required for audio/video merging
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pip dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose the API port
EXPOSE 5000

# Start server bound to all interfaces
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
