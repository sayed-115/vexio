import os
import sys
import subprocess
import json
import shutil

try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.panel import Panel
    from rich.text import Text
except ImportError:
    print("This tool requires the 'rich' library for modern terminal UI.")
    print("Please install required dependencies by running:")
    print("    pip install rich yt-dlp")
    sys.exit(1)

console = Console()
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

def ensure_dependencies():
    """Ensure yt-dlp and ffmpeg are available on the system."""
    try:
        import yt_dlp
    except ImportError:
        console.print("[bold red]Critical Error:[/bold red] 'yt-dlp' is not installed in the current Python environment.")
        console.print("Please install it: [cyan]pip install yt-dlp[/cyan]")
        sys.exit(1)
        
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        
    # Verify ffmpeg
    if not shutil.which("ffmpeg"):
        # Auto-heal Windows terminal restart issues by dynamically finding the winget installation
        localdata = os.environ.get("LOCALAPPDATA", "")
        if localdata:
            ffmpeg_dir = os.path.join(localdata, "Microsoft", "WinGet", "Packages")
            if os.path.exists(ffmpeg_dir):
                import glob
                matches = glob.glob(os.path.join(ffmpeg_dir, "Gyan.FFmpeg*", "**", "bin"), recursive=True)
                if matches:
                    os.environ["PATH"] += os.pathsep + matches[0]
                    # Verify dynamic injection worked
                    if shutil.which("ffmpeg"):
                        return
                        
        console.print("\n[bold yellow]⚠️  Warning: 'ffmpeg' not found even after deep search.[/bold yellow]")
        console.print("High resolution (1080p/4K/8K) merges into single files will fail. They will save as 2 separate files.")

def is_valid_url(url):
    """Basic validation for URL."""
    return url.startswith("http://") or url.startswith("https://")

def fetch_formats(url):
    """
    Fetch available formats. 
    NOTE: While `yt-dlp -F` was requested, parsing its raw text table is notoriously 
    brittle as spacing/columns change. For production-level code, we use `-J` (--dump-json) 
    to retrieve structured metadata, which allows us to cleanly build our own reliable UI table.
    """
    with console.status("[bold cyan]Fetching media information and formats (This may take a moment)...[/bold cyan]", spinner="dots"):
        try:
            # We add --no-playlist and timeout limitations to prevent infinite hangs
            result = subprocess.run(
                [sys.executable, "-m", "yt_dlp", "--no-playlist", "--socket-timeout", "15", "-J", url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                encoding="utf-8",
                timeout=60
            )
            data = json.loads(result.stdout)
            return data
        except subprocess.TimeoutExpired:
            console.print("\n[bold red]Error:[/bold red] Fetching formats timed out (took over 60s).")
            console.print("[dim]This usually happens if YouTube delays the metadata request, or network connectivity is unstable.[/dim]")
            return None
        except subprocess.CalledProcessError as e:
            console.print(f"\n[bold red]Error fetching formats:[/bold red] {e.stderr.strip()}")
            return None
        except json.JSONDecodeError:
            console.print("\n[bold red]Error:[/bold red] Could not parse format data returned by yt-dlp.")
            return None

def format_size(bytes_size):
    """Convert bytes to readable MB/GB representation."""
    if not bytes_size:
        return "Unknown"
    mb = bytes_size / (1024 * 1024)
    if mb >= 1024:
        gb = mb / 1024
        return f"{gb:.2f} GB"
    return f"{mb:.1f} MB"

def display_format_table(data):
    """Display the fetched formats using a rich UI Table."""
    formats = data.get("formats", [])
    
    table = Table(
        title=f"Available Formats for \n[green]{data.get('title', 'Unknown Media')}[/green]", 
        header_style="bold magenta",
        title_justify="center"
    )
    
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Type", style="green")
    table.add_column("Quality", style="yellow")
    table.add_column("Codec (V/A)", style="dim white")
    table.add_column("Ext", style="blue")
    table.add_column("Size", justify="right", style="bold")
    
    # Sort formats by resolution height (if exists) or width, then fallback to 0
    formats = sorted(formats, key=lambda x: x.get('height') or x.get('width') or 0)

    for fmt in formats:
        fmt_id = str(fmt.get("format_id", "N/A"))
        ext = fmt.get("ext", "N/A")
        vcodec = fmt.get("vcodec", "none")
        acodec = fmt.get("acodec", "none")
        
        # Determine media type classification
        if vcodec != "none" and acodec != "none":
            mtype = "[bold cyan]video+audio[/]"
        elif vcodec != "none":
            mtype = "video"
        elif acodec != "none":
            mtype = "[yellow]audio[/yellow]"
        else:
            continue # Skip ambiguous or data-only tracks
        
        # Determine visual quality metric
        if "video" in mtype:
            height = fmt.get("height")
            fps = fmt.get("fps")
            fps_str = f" {fps}fps" if fps else ""
            quality = f"{height}p{fps_str}".strip() if height else "Unknown"
        else:
            abr = fmt.get("abr")
            quality = f"{int(abr)}k" if abr else "Unknown"
            
        # Codecs preview
        v_c = "none" if vcodec == "none" else vcodec.split(".")[0]
        a_c = "none" if acodec == "none" else acodec.split(".")[0]
        codecs_str = f"{v_c} / {a_c}"
        
        # File Size
        filesize = fmt.get("filesize") or fmt.get("filesize_approx")
        size_str = format_size(filesize)
        
        # Filter out overly obscure fragments to keep the UI clean, 
        # but allow essential streams. 
        if "storyboard" in fmt_id or "m3u8" in fmt.get("protocol", ""):
            continue
            
        table.add_row(fmt_id, mtype, quality, codecs_str, ext, size_str)
        
    console.print(table)
    console.print("[dim italic]Tip: You can combine IDs using '+' (e.g., 137+140) to merge specific video and audio.[/dim italic]")

def download_media(url, format_choice, is_audio=False, audio_mode="mp3"):
    """Executes the download with yt-dlp."""
    # Ensure merge-output-format isn't passed when audio is extracted to prevent errors
    if is_audio:
        base_cmd = [sys.executable, "-m", "yt_dlp", url, "-P", DOWNLOAD_DIR, "-o", "%(title)s.%(ext)s"]
        if audio_mode == "mp3":
            # Best possible VBR 0 MP3 (equivalent to 320kbps)
            cmd = base_cmd + ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            # Exact 1:1 bit-for-bit native youtube audio (Opus/AAC)
            cmd = base_cmd + ["-f", "bestaudio/best", "-x"]
    else:
        base_cmd = [sys.executable, "-m", "yt_dlp", url, "-P", DOWNLOAD_DIR, "-o", "%(title)s.%(ext)s", "--merge-output-format", "mp4"]
        if format_choice == "best":
            cmd = base_cmd + ["-f", "bestvideo+bestaudio/best"]
        elif format_choice == "best_under_720p":
            cmd = base_cmd + ["-f", "bestvideo[height<=720]+bestaudio/best[height<=720]"]
        else:
            # Custom format provided by user
            cmd = base_cmd + ["-f", format_choice]

    command_str = " ".join(cmd)
    console.print(f"\n[bold blue]🚀 Running:[/bold blue] [dim]{command_str}[/dim]\n")
    
    try:
        # Not capturing stdout/stderr allows the user to see the native yt-dlp progress bar
        subprocess.run(cmd, check=True)
        console.print(f"\n[bold green]✅ Download Completed Successfully![/bold green]")
        console.print(f"📁 Saved in directory: [bold cyan]{os.path.abspath(DOWNLOAD_DIR)}[/bold cyan]")
    except subprocess.CalledProcessError:
        console.print("\n[bold red]❌ Download Failed. Please carefully check the error output above.[/bold red]")

def display_main_header():
    """Prints the application banner."""
    header = Panel(
        "[bold cyan]=== Advanced CLI Media Downloader ===[/bold cyan]\n"
        "[dim]Powered by yt-dlp & Rich Terminal UI[/dim]", 
        expand=False,
        border_style="magenta"
    )
    console.print(header)
        
def main():
    display_main_header()
    ensure_dependencies()
    
    while True:
        url = Prompt.ask("\n[bold yellow]🔗 Enter Media URL[/bold yellow] (or type 'q' to quit)").strip()
        
        if url.lower() in ['q', 'quit', 'exit']:
            console.print("[dim]Goodbye![/dim] 👋\n")
            break
            
        if not is_valid_url(url):
            console.print("[bold red]Invalid URL format. Please start with http:// or https://[/bold red]")
            continue
            
        # Extract format information first to confirm video exists and get title
        media_data = fetch_formats(url)
        if not media_data:
            continue
            
        console.print(f"\n[bold green]🎯 Target:[/bold green] {media_data.get('title', 'Unknown Media')}")
        
        
        # Extract unique resolutions dynamically
        formats = media_data.get("formats", [])
        resolutions = sorted(list(set(
            f.get("height") for f in formats if f.get("height") and f.get("vcodec") != "none"
        )), reverse=True)
        
        # Filter down to common recognizable resolutions to keep menu clean
        common_res = [res for res in resolutions if res in [4320, 2160, 1440, 1080, 720, 480, 360]]
        if not common_res and resolutions:
            common_res = [resolutions[0]] # ensure at least max quality is presesnt
            
        while True:
            console.print("\n[bold underline]Download Quality Options:[/bold underline]")
            
            choices = []
            idx = 1
            for res in common_res:
                # Label standard ones
                label = f"{res}p"
                if res == 2160: label = "4K (2160p)"
                elif res == 4320: label = "8K (4320p)"
                
                console.print(f"  [cyan]{idx}.[/cyan] {label} Video [dim](Auto-merges highest quality audio)[/dim]")
                choices.append(str(idx))
                idx += 1
                
            audio_best_idx = str(idx)
            console.print(f"  [cyan]{audio_best_idx}.[/cyan] Audio Only (Best Quality Native) [dim](Opus/M4A Format - Highest Quality)[/dim]")
            choices.append(audio_best_idx)
            idx += 1
            
            audio_mp3_idx = str(idx)
            console.print(f"  [cyan]{audio_mp3_idx}.[/cyan] Audio Only (MP3 Format) [dim](320kbps - Highly Compatible)[/dim]")
            choices.append(audio_mp3_idx)
            idx += 1
            
            raw_idx = str(idx)
            console.print(f"  [cyan]{raw_idx}.[/cyan] Developer Mode [dim](View raw streams & custom IDs)[/dim]")
            choices.append(raw_idx)
            idx += 1
            
            back_idx = str(idx)
            console.print(f"  [cyan]{back_idx}.[/cyan] Go back [dim](Enter a new URL)[/dim]")
            choices.append(back_idx)
            
            choice = Prompt.ask("\n[bold yellow]Select Format[/bold yellow]", choices=choices)
            
            if choice == audio_best_idx:
                download_media(url, "None", is_audio=True, audio_mode="native")
                break
            elif choice == audio_mp3_idx:
                download_media(url, "None", is_audio=True, audio_mode="mp3")
                break
            elif choice == raw_idx:
                display_format_table(media_data)
                custom_id = Prompt.ask(
                    "\n[bold yellow]Enter Format ID(s) to download[/bold yellow]\n"
                    "[dim](Examples: '22', '140', or '137+140')[/dim]"
                ).strip()
                if custom_id:
                    download_media(url, custom_id)
                break
            elif choice == back_idx:
                break
            else:
                # We know they picked a dynamic resolution
                picked_res = common_res[int(choice) - 1]
                # Format string to grab the best video less-than/equal-to the resolution, and best audio
                fmt_str = f"bestvideo[height<={picked_res}]+bestaudio/best[height<={picked_res}]"
                download_media(url, fmt_str)
                break
                
        console.print("\n" + "━"*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]⏹️ Operation cancelled by user. Exiting...[/bold red]")
        sys.exit(0)
