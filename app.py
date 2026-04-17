import os
import uuid
import glob
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI(title="Premium Media Downloader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_downloads"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

download_jobs = {}

class URLRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_id: str
    is_audio: bool

def get_ffmpeg_path():
    """Automatically locate winget ffmpeg or local workspace ffmpeg."""
    localdata = os.environ.get("LOCALAPPDATA", "")
    if localdata:
        ffmpeg_dir = os.path.join(localdata, "Microsoft", "WinGet", "Packages")
        if os.path.exists(ffmpeg_dir):
            matches = glob.glob(os.path.join(ffmpeg_dir, "Gyan.FFmpeg*", "**", "bin"), recursive=True)
            if matches:
                return matches[0]
    return "."

@app.post("/api/info")
def fetch_info(req: URLRequest):
    try:
        ydl_opts = {'no_playlist': True, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            formats = info.get("formats", [])
            
            resolutions = sorted(list(set(
                f.get("height") for f in formats if f.get("height") and f.get("vcodec") != "none"
            )), reverse=True)
            
            common_res = [res for res in resolutions if res in [4320, 2160, 1440, 1080, 720, 480, 360]]
            if not common_res and resolutions:
                common_res = [resolutions[0]]
                
            return {
                "title": info.get("title", "Unknown Video"),
                "thumbnail": info.get("thumbnail"),
                "resolutions": common_res
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def download_hook(job_id: str):
    def progress(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                download_jobs[job_id]["percent"] = round(percent, 1)
        elif d['status'] == 'finished':
            download_jobs[job_id]["status"] = "merging"
    return progress

def background_download(job_id: str, url: str, format_choice: str, is_audio: bool):
    try:
        ydl_opts = {
            'outtmpl': os.path.join(TEMP_DIR, f"{job_id}_%(title)s.%(ext)s"),
            'progress_hooks': [download_hook(job_id)],
            'format': format_choice,
            'merge_output_format': 'mp4',
            'no_playlist': True,
            'ffmpeg_location': get_ffmpeg_path(),
            'concurrent_fragment_downloads': 10
        }
        
        if is_audio:
            ydl_opts['extract_audio'] = True
            ydl_opts['format'] = 'bestaudio/best' if format_choice == 'native' else 'bestaudio'
            if format_choice == 'mp3':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '0',
                }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            
            final_files = glob.glob(os.path.join(TEMP_DIR, f"{job_id}_*"))
            if final_files:
                download_jobs[job_id]["status"] = "finished"
                download_jobs[job_id]["percent"] = 100
                download_jobs[job_id]["file_path"] = final_files[0]
            else:
                download_jobs[job_id]["status"] = "error"
                download_jobs[job_id]["error"] = "File not generated"

    except Exception as e:
        download_jobs[job_id]["status"] = "error"
        download_jobs[job_id]["error"] = str(e)


@app.post("/api/prepare")
def prepare_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    download_jobs[job_id] = {
        "status": "downloading",
        "percent": 1.0,
        "file_path": None,
        "error": None
    }
    
    fmt_str = req.format_id
    if not req.is_audio and req.format_id.isdigit():
         res = int(req.format_id)
         fmt_str = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]"
         
    background_tasks.add_task(background_download, job_id, req.url, fmt_str, req.is_audio)
    return {"job_id": job_id}

@app.get("/api/progress/{job_id}")
def check_progress(job_id: str):
    job = download_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/serve/{job_id}")
def serve_file(job_id: str):
    job = download_jobs.get(job_id)
    if not job or job["status"] != "finished" or not job["file_path"]:
        raise HTTPException(status_code=400, detail="File is not ready")
        
    file_path = job["file_path"]
    filename = os.path.basename(file_path).split('_', 1)[-1]
    return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream', headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})

# Serve Frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=5000)
