"""
AURA - Premium CLI Media Downloader
Powered by yt-dlp
"""

import os
import sys
import subprocess
import json
import shutil
import glob
import re


# ── Pre-flight ───────────────────────────────────────────────────────────────

try:
    from rich.console import Console
    from rich.text import Text
    from rich.prompt import Prompt
    from rich.markup import escape
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.progress import (
        Progress, BarColumn, TextColumn,
        TaskProgressColumn, SpinnerColumn,
    )
except ImportError:
    print("\n  Missing: rich\n  Install: pip install rich yt-dlp\n")
    sys.exit(1)

try:
    import yt_dlp
except ImportError:
    print("\n  Missing: yt-dlp\n  Install: pip install yt-dlp\n")
    sys.exit(1)


# ── Configuration ────────────────────────────────────────────────────────────

console = Console(highlight=False)

DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR    = os.path.join(SCRIPT_DIR, ".cache", "yt-dlp")

_enc = (getattr(sys.stdout, "encoding", "") or "").lower()
UNI  = "utf" in _enc

SYM = {
    "arrow": "\u2192" if UNI else "->",
    "check": "\u2713" if UNI else "+",
    "cross": "\u2717" if UNI else "x",
    "bolt":  "\u26a1" if UNI else "*",
    "dot":   "\u00b7" if UNI else ".",
    "line":  "\u2500" if UNI else "-",
    "music": "\u266b" if UNI else "#",
}

# Color palette
C = "#58a6ff"   # cyan   - primary / actions
G = "#3fb950"   # green  - success
P = "#bc8cff"   # purple - accents
O = "#f0883e"   # orange - highlights
D = "#6e7681"   # dim    - secondary text
W = "#d29922"   # yellow - warnings

# Proxy
_PROXY_KEYS = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
)
_BAD_PROXIES = {
    "http://127.0.0.1:9", "https://127.0.0.1:9",
    "http://localhost:9",  "https://localhost:9",
    "socks5://127.0.0.1:9", "socks5h://127.0.0.1:9",
}
_warned = {}

# Progress parsing
_DL_PCT_RE   = re.compile(r'\[download\]\s+([\d.]+)%')
_DL_SPEED_RE = re.compile(r'at\s+(\S+/s)')
_DL_ETA_RE   = re.compile(r'ETA\s+(\S+)')


# ── Display Helpers ──────────────────────────────────────────────────────────

def header():
    console.print()
    hdr = Text()
    hdr.append(f"  {SYM['bolt']} ", style=f"bold {P}")
    hdr.append("AURA", style=f"bold {C}")
    hdr.append(f"  {SYM['dot']} ", style=D)
    hdr.append("media downloader", style=D)
    console.print(hdr)
    console.print(f"  [{D}]{SYM['line'] * 38}[/]")
    console.print()




def ok(msg):
    console.print(f"  [{G}]{SYM['check']}[/] {msg}")


def fail(msg):
    console.print(f"  [red]{SYM['cross']}[/] {msg}")


def warn_once(key, msg):
    if key not in _warned:
        console.print(f"  [{W}]![/] [{D}]{msg}[/]")
        _warned[key] = True


def thin_sep():
    console.print(f"  [{D}]{SYM['line'] * 40}[/]")


def fmt_size(b):
    if not b:
        return "?"
    mb = b / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB" if mb >= 10 else f"{mb:.1f} MB"


def fmt_dur(secs):
    if not secs:
        return ""
    s = int(secs)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ── Runtime Environment ─────────────────────────────────────────────────────

def clean_env():
    env = os.environ.copy()
    for k in _PROXY_KEYS:
        if env.get(k, "").strip().lower() in _BAD_PROXIES:
            env.pop(k, None)
            warn_once("proxy", "Ignoring broken proxy (127.0.0.1:9)")
    return env


def js_runtime():
    for rt in ("node", "deno", "bun"):
        if shutil.which(rt):
            return rt
    return None


def yt_cmd(args):
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--cache-dir", CACHE_DIR,
        "--concurrent-fragments", "4",
    ]
    js = js_runtime()
    if js:
        cmd += ["--js-runtimes", js, "--remote-components", "ejs:github"]
    else:
        warn_once("js", "No JS runtime (node/deno/bun) - some formats may be missing")
    return cmd + args


def setup():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not shutil.which("ffmpeg"):
        ld = os.environ.get("LOCALAPPDATA", "")
        if ld:
            pkg = os.path.join(ld, "Microsoft", "WinGet", "Packages")
            if os.path.exists(pkg):
                for m in glob.glob(
                    os.path.join(pkg, "Gyan.FFmpeg*", "**", "bin"),
                    recursive=True,
                ):
                    os.environ["PATH"] += os.pathsep + m
                    if shutil.which("ffmpeg"):
                        return
        warn_once("ffmpeg", "ffmpeg not found - merges may save separate files")


# ── Core Functions ───────────────────────────────────────────────────────────

def fetch(url):
    """Fetch format metadata with animated spinner."""
    spinner = console.status(
        Text.assemble((f"  {SYM['arrow']} ", C), ("Fetching formats...", "")),
        spinner="dots" if UNI else "line",
    )
    spinner.start()

    try:
        r = subprocess.run(
            yt_cmd(["--no-playlist", "--socket-timeout", "15", "-J", url]),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            encoding="utf-8",
            timeout=60,
            env=clean_env(),
        )
        data = json.loads(r.stdout)
    except subprocess.TimeoutExpired:
        data, err = None, "Timed out (60s)"
    except subprocess.CalledProcessError as e:
        data, err = None, escape(e.stderr.strip()[:200])
    except json.JSONDecodeError:
        data, err = None, "Could not parse response"
    else:
        err = None
    finally:
        spinner.stop()

    if data:
        ok("Formats loaded")
        return data
    else:
        fail(err)
        return None


def show_target(data):
    """Display video info in a styled panel."""
    title = escape(data.get("title", "Unknown"))
    uploader = escape(
        data.get("uploader") or data.get("channel")
        or data.get("channel_id") or "Unknown"
    )
    dur = fmt_dur(data.get("duration"))

    content = Text()
    content.append(title, style="bold")
    content.append("\n")
    meta = uploader
    if dur:
        meta += f" {SYM['dot']} {dur}"
    content.append(meta, style=D)

    panel = Panel(
        content,
        border_style=P,
        box=box.ROUNDED,
        padding=(0, 2),
    )
    console.print(panel)
    console.print()


def _best_vid_size(fmts, h):
    cands = [f for f in fmts if f.get("height") == h and f.get("vcodec") != "none"]
    if not cands:
        return 0
    return max(
        (f.get("filesize") or f.get("filesize_approx") or 0 for f in cands),
        default=0,
    )


def format_menu(data):
    """Display numbered format menu and return selection."""
    fmts = data.get("formats", [])

    resolutions = sorted(
        set(f.get("height") for f in fmts if f.get("height") and f.get("vcodec") != "none"),
        reverse=True,
    )[:10]

    ba_kbps, ba_ext, ba_size = 0, "", 0
    for f in fmts:
        if f.get("acodec") != "none" and f.get("vcodec") == "none":
            abr = f.get("abr") or f.get("tbr") or 0
            if abr > ba_kbps:
                ba_kbps = abr
                ba_ext = f.get("ext", "?").upper()
                ba_size = f.get("filesize") or f.get("filesize_approx") or 0

    audio_msg = "highest quality audio"
    if ba_kbps > 0:
        audio_msg = f"{int(ba_kbps)}kbps {ba_ext} audio"

    # ── Video options ────────────────────────────────────────────────────
    choices = []
    idx = 1
    is_best = True

    for res in resolutions:
        base_label = f"{res}p"
        if res == 4320:
            base_label = "8K (4320p)"
        elif res == 2160:
            base_label = "4K (2160p)"
        elif res == 1440:
            base_label = "1440p"

        vs = _best_vid_size(fmts, res)
        total = vs + ba_size
        sz = fmt_size(total) if total > 0 else "~Unknown"

        line = Text()
        line.append(f"  {idx:>2}. ", style=C)
        line.append(f"{base_label} ", style="bold")
        if is_best:
            line.append("(Highest Quality) ", style=f"italic {P}")
            is_best = False
        line.append("Video ", style="bold")
        line.append(f"[{sz}] ", style=G)
        line.append(f"(Auto-merges {audio_msg})", style=D)
        console.print(line)
        choices.append(str(idx))
        idx += 1

    thin_sep()

    # ── Audio options ────────────────────────────────────────────────────
    asz = fmt_size(ba_size) if ba_size > 0 else "~Unknown"
    native_desc = f"{int(ba_kbps)}kbps {ba_ext} Format" if ba_kbps else "Opus/M4A Format"
    mp3_desc = f"Transcoded ~{int(ba_kbps)}kbps MP3" if ba_kbps else "320kbps MP3"

    audio_idx = str(idx)
    line = Text()
    line.append(f"  {idx:>2}. ", style=C)
    line.append(f"{SYM['music']} ", style=P)
    line.append("Audio Only ", style="bold")
    line.append("(Best Quality Native) ", style=f"{P}")
    line.append(f"[{asz}] ", style=G)
    line.append(f"({native_desc} - Highest Quality)", style=D)
    console.print(line)
    choices.append(audio_idx)
    idx += 1

    mp3_idx = str(idx)
    line = Text()
    line.append(f"  {idx:>2}. ", style=C)
    line.append(f"{SYM['music']} ", style=O)
    line.append("Audio Only ", style="bold")
    line.append("(MP3 Format) ", style=f"{O}")
    line.append(f"[{asz}] ", style=G)
    line.append(f"({mp3_desc} - Highly Compatible)", style=D)
    console.print(line)
    choices.append(mp3_idx)
    idx += 1

    thin_sep()

    # ── Other options ────────────────────────────────────────────────────
    dev_idx = str(idx)
    line = Text()
    line.append(f"  {idx:>2}. ", style=C)
    line.append("Developer Mode ", style=f"bold {O}")
    line.append("(View raw streams & custom IDs)", style=D)
    console.print(line)

    line = Text()
    line.append("   0. ", style=C)
    line.append("Go back ", style=D)
    line.append("(enter a new URL)", style=D)
    console.print(line)
    choices.append(dev_idx)
    choices.extend(["0", "b", "B"])

    console.print()
    choice = Prompt.ask(
        Text.assemble((f"  {SYM['arrow']} ", C), ("Select format", "")),
        choices=choices,
    )

    return choice, resolutions, audio_idx, mp3_idx, dev_idx


def dev_mode(data):
    """Show raw format table for developer mode."""
    fmts = sorted(
        data.get("formats", []),
        key=lambda x: x.get("height") or x.get("width") or 0,
    )

    table = Table(
        title="Available Streams",
        title_style=f"bold {C}",
        box=box.ROUNDED,
        border_style=D,
        header_style="bold",
        padding=(0, 1),
        show_lines=False,
    )
    table.add_column("ID", style=C, min_width=6)
    table.add_column("Type", style="", min_width=11)
    table.add_column("Quality", style=P, min_width=10)
    table.add_column("Codec", style=D, min_width=14)
    table.add_column("Size", style=G, justify="right", min_width=8)

    for f in fmts:
        fid = str(f.get("format_id", "?"))
        vc = f.get("vcodec", "none")
        ac = f.get("acodec", "none")

        if vc != "none" and ac != "none":
            mt = "video+audio"
        elif vc != "none":
            mt = "video"
        elif ac != "none":
            mt = "audio"
        else:
            continue

        if "storyboard" in fid or "m3u8" in f.get("protocol", ""):
            continue

        if "video" in mt:
            h = f.get("height")
            fps = f.get("fps")
            q = f"{h}p" if h else "?"
            if fps:
                q += f" {fps}fps"
        else:
            abr = f.get("abr")
            q = f"{int(abr)}k" if abr else "?"

        v = "none" if vc == "none" else vc.split(".")[0]
        a = "none" if ac == "none" else ac.split(".")[0]
        sz = fmt_size(f.get("filesize") or f.get("filesize_approx"))

        table.add_row(fid, mt, q, f"{v}/{a}", sz)

    console.print(table)
    console.print()
    console.print(f"  [{D}]Tip: combine IDs with + (e.g. 137+140)[/]")
    console.print()


def do_download(url, fmt, is_audio=False, audio_mode="mp3"):
    """Execute download with yt-dlp and show a live progress bar."""
    # Smart filename template
    if "youtube.com" in url.lower() or "youtu.be" in url.lower():
        tpl = "%(title).60s_[%(id)s].%(ext)s"
    else:
        tpl = "%(extractor_key)s_%(uploader|Video)s_[%(id)s].%(ext)s"

    if is_audio:
        base = yt_cmd([url, "-P", DOWNLOAD_DIR, "-o", tpl, "--restrict-filenames"])
        if audio_mode == "mp3":
            cmd = base + ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            cmd = base + ["-f", "bestaudio/best", "-x"]
    else:
        base = yt_cmd([
            url, "-P", DOWNLOAD_DIR, "-o", tpl,
            "--restrict-filenames", "--merge-output-format", "mp4",
        ])
        cmd = base + ["-f", fmt]

    # Flags for clean parseable output
    cmd.extend(["--newline", "--no-colors"])

    # Snapshot download directory to detect new file afterwards
    existing = set()
    for f in os.listdir(DOWNLOAD_DIR):
        fp = os.path.join(DOWNLOAD_DIR, f)
        if os.path.isfile(fp):
            existing.add(fp)

    env = clean_env()
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,
    )

    with Progress(
        SpinnerColumn(style=P, spinner_name="dots" if UNI else "line"),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=30, style=D, complete_style=C, finished_style=G),
        TaskProgressColumn(),
        TextColumn("{task.fields[stats]}", style=D),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("  Downloading", total=100, stats="")
        is_processing = False

        for raw in iter(process.stdout.readline, ""):
            line = raw.rstrip("\n\r").strip()
            if not line:
                continue

            pct_m = _DL_PCT_RE.search(line)
            if pct_m:
                pct = float(pct_m.group(1))

                # Switch back from processing mode if new download starts
                if is_processing:
                    progress.update(task, description="  Downloading", total=100)
                    is_processing = False

                stats_parts = []
                speed_m = _DL_SPEED_RE.search(line)
                if speed_m and "Unknown" not in speed_m.group(1):
                    stats_parts.append(speed_m.group(1))
                eta_m = _DL_ETA_RE.search(line)
                if eta_m and "Unknown" not in eta_m.group(1):
                    stats_parts.append(f"ETA {eta_m.group(1)}")

                progress.update(
                    task,
                    completed=min(pct, 100),
                    stats=" ".join(stats_parts),
                )

            elif "[Merger]" in line or "[ExtractAudio]" in line:
                progress.update(
                    task,
                    description="  Processing",
                    total=None,
                    completed=0,
                    stats="",
                )
                is_processing = True

            elif "has already been downloaded" in line:
                progress.update(task, completed=100, stats="cached")

            elif "ERROR" in line:
                progress.console.print(f"  [red]{SYM['cross']}[/] {escape(line)}")

    process.wait()
    console.print()

    if process.returncode == 0:
        # Detect the newly downloaded file for a nice summary
        new_files = []
        for f in os.listdir(DOWNLOAD_DIR):
            fp = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(fp) and fp not in existing:
                new_files.append(fp)

        if new_files:
            newest = max(new_files, key=os.path.getmtime)
            size = os.path.getsize(newest)
            ok(f"Completed {SYM['dot']} {fmt_size(size)}")
            console.print(f"  [{D}]{os.path.basename(newest)}[/]")
        else:
            ok("Completed")

        console.print(f"  [{D}]{DOWNLOAD_DIR}[/]\n")
    else:
        fail("Download failed\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    setup()
    header()

    while True:
        url = Prompt.ask(
            Text.assemble((f"  {SYM['arrow']} ", C), ("URL", ""))
        ).strip()

        if not url or url.lower() in ("q", "quit", "exit"):
            console.print(f"\n  [{D}]Goodbye.[/]\n")
            break

        if not (url.startswith("http://") or url.startswith("https://")):
            fail("Invalid URL - must start with http:// or https://")
            continue

        console.print()
        data = fetch(url)
        if not data:
            continue

        console.print()

        # Format selection loop
        while True:
            show_target(data)
            choice, resolutions, audio_idx, mp3_idx, dev_idx = format_menu(data)

            if choice in ("0", "b", "B"):
                console.print()
                break

            console.print()

            if choice == audio_idx:
                do_download(url, "", is_audio=True, audio_mode="native")
                break

            elif choice == mp3_idx:
                do_download(url, "", is_audio=True, audio_mode="mp3")
                break

            elif choice == dev_idx:
                dev_mode(data)
                custom = Prompt.ask(
                    Text.assemble((f"  {SYM['arrow']} ", C), ("Format ID(s)", ""))
                ).strip()
                if custom and custom.lower() not in ("b", "back", "0"):
                    console.print()
                    do_download(url, custom)
                break

            else:
                picked_res = resolutions[int(choice) - 1]
                fmt = f"bestvideo[height<={picked_res}]+bestaudio/best[height<={picked_res}]"
                do_download(url, fmt)
                break


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        console.print(f"\n\n  [{D}]Cancelled.[/]\n")
        sys.exit(0)
