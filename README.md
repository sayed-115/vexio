# AURA - Media Downloader

A premium CLI tool for downloading and archiving maximum-quality media from YouTube and other platforms. Powered by `yt-dlp`.

## Features

* **Fast parallel downloads** — concurrent fragment downloading for maximum speed
* **Smart quality menu** — pick from 8K to 144p with estimated file sizes
* **Audio extraction** — native Opus/WEBM or transcoded MP3
* **Developer mode** — inspect raw streams and use custom format IDs
* **Auto FFmpeg merging** — combines video + audio into standalone `.mp4`
* **Cross-platform** — works on Windows, macOS, and Linux

## Quick Start

### Windows
Double-click `start.bat` — it creates a virtual environment, installs dependencies, and launches AURA.

### Manual
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python downloader.py
```

## Requirements

* Python 3.8+
* FFmpeg (for merging video/audio streams)
* Node.js, Deno, or Bun (optional — enables additional format extraction)
