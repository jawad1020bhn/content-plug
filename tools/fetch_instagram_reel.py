#!/usr/bin/env python3
"""One-shot importer for a public Instagram reel.

Prefers yt-dlp's format metadata: download the best video-only and audio-only
CDN streams directly, then mux them with ffmpeg into one MP4. Falls back to
yt-dlp's own downloader, raw CDN URLs, and instaloader. Also writes debug
metadata to reel-debug/ for the workflow artifact.
"""
import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
CREATOR = "Quran Recitations (@beautiful.quran.recitation)"
POSTED = "2026-07-15"
AUDIO = "Jahed Al-Hasan • Qala Inni Abdullahi"
CAPTION = (
    "(The Largest Community Iftar in the World – Matariya Iftar) Around 40 streets in "
    "the Matariya district were transformed into one giant Ramadan iftar table, welcoming "
    "more than 100,000 fasting people during the annual community iftar organized by the "
    "residents of the area. The iftar tables stretched across long distances through the "
    "streets, while volunteers from the neighborhood’s youth and residents worked since "
    "early hours preparing and arranging tables and chairs to welcome visitors coming from "
    "different parts of Cairo to participate in this unique event. During the preparations, "
    "the people of Matariya successfully prepared nearly 100,000 iftar meals, which were "
    "distributed to fasting attendees at the moment of Maghrib prayer, in a Ramadan "
    "atmosphere filled with joy, generosity, and the spirit of sharing. The event was "
    "attended by a large number of visitors and guests who were eager to witness this "
    "remarkable occasion up close, as the area turned into a vibrant festival reflecting "
    "the generosity of Egyptians and their strong sense of community during the holy month "
    "of Ramadan."
)
DEBUG_DIR = Path("reel-debug")


def log(msg):
    print(f"[fetch-reel] {msg}", flush=True)


def write_debug(name, text):
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (DEBUG_DIR / name).write_text(str(text), encoding="utf-8")
    except Exception as e:
        log(f"could not write debug {name}: {e}")


def http_get(url, headers=None, timeout=90):
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def clean_url(u):
    u = u.strip().rstrip('\\,)}]>"\'')
    u = u.replace("\\u0026", "&").replace("\\u0025", "%").replace("\\/", "/")
    u = html.unescape(u)
    try:
        u = json.loads('"' + u.replace('"', '\\"') + '"')
    except Exception:
        pass
    return u.strip()


def extract_urls(text):
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    text = text.replace("\\u0026", "&").replace("\\u0025", "%").replace("\\/", "/")
    patterns = [
        r'<meta[^>]+(?:property|name)=["\'](?:og:video|og:video:url|twitter:player:stream)["\'][^>]+content=["\']([^"\']+)',
        r'"(?:video_url|playback_url|contentUrl|audio_src|audio_url|src|url)"\s*:\s*"([^"]+)"',
        r'https?[^"\'<>\s\\]+?\.(?:mp4|m4a|mp3|webm)[^"\'<>\s\\]*',
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            raw = m.group(1) if m.lastindex else m.group(0)
            u = clean_url(raw)
            if u.startswith("http") and any(k in u.lower() for k in ("cdninstagram", ".mp4", ".m4a", ".mp3", ".webm", "audio", "video")):
                found.append(u)
    seen, out = set(), []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def urls_from_obj(obj):
    out = []
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, str):
                u = clean_url(v)
                if u.startswith("http") and any(k in u.lower() for k in ("cdninstagram", ".mp4", ".m4a", ".mp3", ".webm", "audio", "video")):
                    out.append(u)
            else:
                out.extend(urls_from_obj(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(urls_from_obj(v))
    return out


def rank(u):
    low = u.lower()
    score = 0
    for token, points in (("1080", 5), ("720", 4), ("progressive", 3), ("640", 3), ("hd", 2), ("sd", 2)):
        if token in low:
            score += points
    if any(ext in low for ext in (".m4a", ".mp3")) or "audio" in low:
        score -= 10
    return -score


def jina_html(page_url):
    reader = "https://r.jina.ai/" + page_url
    data, _ = http_get(
        reader,
        headers={"x-respond-with": "html", "x-no-cache": "true", "Accept": "text/html"},
        timeout=120,
    )
    return data.decode("utf-8", "replace")


def instagram_html(page_url):
    data, _ = http_get(page_url, headers={"Accept": "text/html"}, timeout=90)
    return data.decode("utf-8", "replace")


def api_urls(shortcode):
    urls = []
    for base in (
        "https://www.instagram.com/api/v1/media/shortcode/",
        "https://i.instagram.com/api/v1/media/shortcode/",
    ):
        endpoint = f"{base}{shortcode}/info/"
        try:
            data, _ = http_get(
                endpoint,
                headers={"x-ig-app-id": "936619743392459", "Accept": "application/json"},
                timeout=60,
            )
            obj = json.loads(data)
            found = urls_from_obj(obj)
            log(f"api {endpoint} -> {len(found)} urls")
            urls.extend(found)
        except Exception as e:
            log(f"api {endpoint} failed: {e}")
    return urls


def collect_urls(page_url, shortcode):
    embed = f"https://www.instagram.com/reel/{shortcode}/embed/captioned/"
    sources = (
        ("jina-main", lambda: jina_html(page_url)),
        ("jina-embed", lambda: jina_html(embed)),
        ("ig-main", lambda: instagram_html(page_url)),
        ("ig-embed", lambda: instagram_html(embed)),
    )
    all_urls = []
    for name, fn in sources:
        try:
            text = fn()
            write_debug(f"{name}.html", text)
            found = extract_urls(text)
            write_debug(f"{name}.urls.txt", "\n".join(found) + "\n")
            log(f"{name}: {len(found)} candidate urls")
            all_urls.extend(found)
        except Exception as e:
            log(f"{name} failed: {e}")
    all_urls.extend(api_urls(shortcode))
    final = sorted(set(all_urls), key=rank)
    write_debug("all-candidates.txt", "\n".join(final) + "\n")
    return final


def write_ytdlp_debug(page_url):
    jobs = (
        ("ytdlp-formats.txt", [sys.executable, "-m", "yt_dlp", "-F", "--no-warnings", page_url]),
        ("ytdlp-info.json", [sys.executable, "-m", "yt_dlp", "--dump-single-json", "--no-warnings", page_url]),
    )
    info = None
    for name, cmd in jobs:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            body = p.stdout or ""
            if p.stderr:
                body += "\n--- stderr ---\n" + p.stderr
            write_debug(name, body)
            if name == "ytdlp-info.json" and p.stdout.strip():
                try:
                    info = json.loads(p.stdout)
                except Exception as e:
                    log(f"could not parse yt-dlp info: {e}")
        except Exception as e:
            write_debug(name, f"failed: {e}")
    return info


def probe_types(path):
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {line.strip() for line in p.stdout.splitlines() if line.strip()}
    except Exception as e:
        log(f"ffprobe failed for {path}: {e}")
        return set()


def has_video_audio(path):
    return path.exists() and {"video", "audio"}.issubset(probe_types(path))


def ffmpeg_mux(video, audio, out, reencode=False):
    cmd = ["ffmpeg", "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0"]
    if reencode:
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-c", "copy"]
    cmd += ["-movflags", "+faststart", "-shortest", str(out)]
    log(f"muxing with ffmpeg (reencode={reencode})")
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    write_debug("format-mux.log", (p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or ""))
    if p.returncode == 0 and has_video_audio(out):
        return True
    log(f"ffmpeg mux rc={p.returncode}: {p.stderr[-400:]}")
    return False


def pick_formats(info):
    formats = [f for f in info.get("formats", []) if isinstance(f, dict)]
    videos = [
        f for f in formats
        if f.get("url", "").startswith("http")
        and f.get("vcodec") not in (None, "none")
        and f.get("acodec") in (None, "none")
    ]
    audios = [
        f for f in formats
        if f.get("url", "").startswith("http")
        and f.get("acodec") not in (None, "none")
        and f.get("vcodec") in (None, "none")
    ]
    videos.sort(key=lambda f: (float(f.get("tbr") or 0), (f.get("width") or 0) * (f.get("height") or 0)), reverse=True)
    audios.sort(key=lambda f: float(f.get("tbr") or 0), reverse=True)
    return (videos[0] if videos else None), (audios[0] if audios else None)


def fetch_stream(url, headers, dest):
    data, ct = http_get(url, headers=headers, timeout=180)
    if len(data) < 10000 or data[4:8] != b"ftyp":
        raise ValueError(f"not an MP4 segment (size={len(data)}, magic={data[:12]!r}, content-type={ct})")
    dest.write_bytes(data)
    return dest


def try_direct_formats(info, page_url, out):
    if not info:
        return None
    video_fmt, audio_fmt = pick_formats(info)
    if not video_fmt or not audio_fmt:
        log("yt-dlp info did not contain separate video+audio formats")
        return None
    write_debug("selected-formats.json", json.dumps({"video": video_fmt, "audio": audio_fmt}, ensure_ascii=False, indent=2)[:20000])
    log(f"selected video={video_fmt.get('format_id')} audio={audio_fmt.get('format_id')}")
    headers = dict(info.get("http_headers") or {})
    headers.setdefault("User-Agent", UA)
    headers.setdefault("Referer", page_url)
    headers.setdefault("Accept", "*/*")
    video_path = out.with_name(out.stem + ".video.mp4")
    audio_path = out.with_name(out.stem + ".audio.m4a")
    try:
        fetch_stream(video_fmt["url"], headers, video_path)
        fetch_stream(audio_fmt["url"], headers, audio_path)
    except Exception as e:
        log(f"direct format download failed: {e}")
        video_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
        return None
    if ffmpeg_mux(video_path, audio_path, out, reencode=False) or ffmpeg_mux(video_path, audio_path, out, reencode=True):
        video_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
        return video_fmt["url"]
    video_path.unlink(missing_ok=True)
    audio_path.unlink(missing_ok=True)
    return None


def download_url(u, out):
    log(f"trying direct download: {u[:160]}")
    data, ct = http_get(
        u,
        headers={"Referer": "https://www.instagram.com/", "Accept": "video/mp4,audio/mp4,application/octet-stream,*/*"},
        timeout=180,
    )
    if len(data) < 10000:
        raise ValueError(f"too small ({len(data)} bytes)")
    if data[4:8] != b"ftyp":
        raise ValueError(f"not an MP4 (magic={data[:12]!r}, content-type={ct})")
    out.write_bytes(data)
    return True


def try_urls(urls, out):
    for u in urls:
        try:
            if download_url(u, out):
                return u
        except Exception as e:
            log(f"direct failed: {e}")
    return None


def try_ytdlp(page_url, out):
    base = out.with_name(out.stem + ".ytdlp")
    for old in base.parent.glob(base.name + ".*"):
        old.unlink(missing_ok=True)
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "--force-overwrites",
        "--no-playlist",
        "-o", str(base) + ".%(ext)s",
        page_url,
    ]
    log("trying yt-dlp downloader")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        log(f"yt-dlp error: {e}")
        write_debug("ytdlp-download.log", str(e))
        return False
    write_debug("ytdlp-download.log", (p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or ""))
    if p.returncode != 0:
        log(f"yt-dlp rc={p.returncode}: {p.stderr[-600:]}")
        return False
    merged = base.with_suffix(".mp4")
    if has_video_audio(merged):
        merged.replace(out)
        return True
    videos = sorted(base.parent.glob(base.name + ".f*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    audios = sorted(base.parent.glob(base.name + ".f*.m4a"), key=lambda p: p.stat().st_mtime, reverse=True)
    if videos and audios and ffmpeg_mux(videos[0], audios[0], out, reencode=False):
        return True
    return False


def try_instaloader(shortcode, out):
    try:
        import instaloader

        log("trying instaloader")
        loader = instaloader.Instaloader(
            dirname_pattern="content inputs",
            filename_pattern="{shortcode}",
            download_pictures=True,
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        loader.download_post(post, target="content inputs")
        for p in sorted(Path("content inputs").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
            data = p.read_bytes()
            if len(data) > 10000 and data[4:8] == b"ftyp":
                out.write_bytes(data)
                if p.resolve() != out.resolve():
                    p.unlink(missing_ok=True)
                return True
    except Exception as e:
        log(f"instaloader failed: {e}")
    return False


def write_metadata(out, page_url, shortcode, method, media_url):
    data = out.read_bytes()
    meta = {
        "shortcode": shortcode,
        "source_url": page_url,
        "creator": CREATOR,
        "posted": POSTED,
        "audio": AUDIO,
        "caption": CAPTION,
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "download_method": method,
        "media_host": urlparse(media_url).netloc if media_url else None,
        "filename": out.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "note": "Public Instagram reel supplied by the user. Creator is credited in this sidecar; not posted anywhere.",
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://www.instagram.com/reel/DazBMEAs2aw/")
    ap.add_argument("--shortcode", default="DazBMEAs2aw")
    ap.add_argument("--out", default="content inputs/DazBMEAs2aw.mp4")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    log(f"target={out} url={args.url}")

    urls = collect_urls(args.url, args.shortcode)
    info = write_ytdlp_debug(args.url)

    method = None
    media_url = None
    direct = try_direct_formats(info, args.url, out)
    if direct:
        method = "direct-formats+ffmpeg"
        media_url = direct
    elif try_ytdlp(args.url, out):
        method = "yt-dlp"
    else:
        log(f"total candidate urls={len(urls)}")
        media_url = try_urls(urls, out)
        if media_url:
            method = "direct-cdn"
        elif try_instaloader(args.shortcode, out):
            method = "instaloader"

    if not method:
        log("all download methods failed")
        sys.exit(1)

    data = out.read_bytes()
    if len(data) < 10000 or data[4:8] != b"ftyp" or not has_video_audio(out):
        log("downloaded file is not a valid video+audio MP4")
        sys.exit(1)
    write_metadata(out, args.url, args.shortcode, method, media_url)
    log(f"saved {out} ({len(data)} bytes) via {method}")


if __name__ == "__main__":
    main()
