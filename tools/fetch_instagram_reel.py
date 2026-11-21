#!/usr/bin/env python3
"""One-shot importer for a public Instagram reel.

Tries yt-dlp, direct CDN URLs discovered in the page/embed/API metadata, then
instaloader. Writes an MP4 plus a small JSON sidecar with source/credit info.
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


def log(msg):
    print(f"[fetch-reel] {msg}", flush=True)


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
        r'"(?:video_url|playback_url|contentUrl|src|url)"\s*:\s*"([^"]+)"',
        r'https?[^"\'<>\s\\]+?\.mp4[^"\'<>\s\\]*',
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            raw = m.group(1) if m.lastindex else m.group(0)
            u = clean_url(raw)
            if u.startswith("http") and (".mp4" in u or "cdninstagram" in u or "video" in u):
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
                if u.startswith("http") and (".mp4" in u or "cdninstagram" in u or "video" in u):
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
    return -score


def jina_html(page_url):
    reader = "https://r.jina.ai/" + page_url
    data, _ = http_get(
        reader,
        headers={
            "x-respond-with": "html",
            "x-no-cache": "true",
            "Accept": "text/html",
        },
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
                headers={
                    "x-ig-app-id": "936619743392459",
                    "Accept": "application/json",
                },
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
            found = extract_urls(fn())
            log(f"{name}: {len(found)} candidate urls")
            all_urls.extend(found)
        except Exception as e:
            log(f"{name} failed: {e}")
    all_urls.extend(api_urls(shortcode))
    return sorted(set(all_urls), key=rank)


def download_url(u, out):
    log(f"trying direct download: {u[:160]}")
    data, ct = http_get(
        u,
        headers={
            "Referer": "https://www.instagram.com/",
            "Accept": "video/mp4,application/octet-stream,*/*",
        },
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
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "--no-playlist",
        "--no-warnings",
        "-o",
        str(out),
        page_url,
    ]
    log("trying yt-dlp")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        log(f"yt-dlp error: {e}")
        return False
    if p.returncode != 0:
        log(f"yt-dlp rc={p.returncode}: {p.stderr[-600:]}")
        return False
    if out.exists() and out.stat().st_size > 10000 and out.read_bytes()[4:8] == b"ftyp":
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

    method = None
    media_url = None
    if try_ytdlp(args.url, out):
        method = "yt-dlp"
    else:
        urls = collect_urls(args.url, args.shortcode)
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
    if len(data) < 10000 or data[4:8] != b"ftyp":
        log("downloaded file is not a valid MP4")
        sys.exit(1)
    write_metadata(out, args.url, args.shortcode, method, media_url)
    log(f"saved {out} ({len(data)} bytes) via {method}")


if __name__ == "__main__":
    main()
