# ⚡ AURA — Premium CLI Media Downloader

A blazing-fast, feature-rich CLI media downloader powered by **yt-dlp**. Supports YouTube, Facebook, Instagram, and [1000+ sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Features

| Feature | Description |
|---|---|
| **Smart Quality Menu** | Browse available resolutions with file sizes, pick what you need |
| **Audio Extraction** | Native format (Opus/M4A) or transcoded MP3 with embedded thumbnail |
| **Subtitle Embedding** | Auto-embeds English subtitles (manual + auto-generated) into MP4 |
| **SponsorBlock** | Automatically removes sponsor segments from YouTube videos |
| **Metadata Tags** | Embeds title, artist, date, and description into downloaded files |
| **Playlist Support** | Download entire playlists with a live progress counter |
| **Batch Download** | Feed a `.txt` file of URLs to download them all sequentially |
| **Clipboard Auto-Paste** | Detects URLs in your clipboard — just press Enter |
| **Download History** | Tracks downloaded videos to warn you about duplicates |
| **Quality Presets** | Set a default quality to skip the menu every time |
| **Speed Limiter** | Cap download bandwidth (e.g. `5M`, `10M`) |
| **Custom Save Location** | Change where files are saved from the settings menu |
| **Auto-Update Check** | Checks for yt-dlp updates once per day |
| **Developer Mode** | View raw streams and use custom format IDs |

## Quick Start

```
git clone https://github.com/sayed-115/vexio.git
cd vexio
start.bat
```

That's it. The launcher is self-bootstrapping: it detects Python, rebuilds a broken local environment if needed, installs dependencies, and launches the CLI.

## Self-Bootstrap Behavior (Windows)

`start.bat` is designed to be as independent as possible and recover automatically:

- Runs from the project folder automatically (no manual `cd` needed)
- Detects Python via `py -3`, `python`, and common local install paths
- Attempts automatic Python install via `winget` if Python is missing
- Recreates `venv` when it exists but points to an invalid/removed Python
- Installs requirements into the local `venv` and launches with local interpreter

## Usage

```
→ URL: https://youtube.com/watch?v=...     ← paste a URL (or press Enter for clipboard)
→ URL: s                                    ← open settings
→ URL: C:\path\to\urls.txt                  ← batch download from file
→ URL: q                                    ← quit
```

### Settings Menu

Type `s` at the URL prompt to access:

- **Download directory** — change where files are saved
- **Default quality** — set a preset (e.g. `1080p`, `720p`, `audio_mp3`)
- **Speed limit** — cap bandwidth (e.g. `5M` for 5 MB/s)
- **SponsorBlock** — toggle sponsor segment removal on/off
- **Check for updates** — manually check for package updates
- **Clear history** — reset the download history

### Batch Mode

Create a `.txt` file with one URL per line, then paste the file path:

```
→ URL: C:\Users\me\Desktop\urls.txt
```

### Playlist Mode

Paste a YouTube playlist URL and AURA will detect it automatically:

```
→ URL: https://youtube.com/playlist?list=PL...
```

## Requirements

- Windows 10/11
- Python 3.8+ (auto-detected, and auto-installed via WinGet when possible)
- ffmpeg (auto-detected from WinGet if installed)
- Node.js/Deno/Bun (optional, for some extractors)

## Dependencies

```
rich>=13.0.0
yt-dlp>=2023.10.0
mutagen
```

Installed automatically by `start.bat` into an isolated virtual environment.
