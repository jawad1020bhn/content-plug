#!/usr/bin/env python3
"""Slot 008 audio recon: find downloadable Ghaith Samreen Surah-Taha audio.

Ghaith Samreen is on NO structured per-ayah source (not on QF, mp3quran
reciter search negative, surahquran's 30, or EveryAyah). This recon probes
YouTube candidates via yt-dlp: duration, chapters, description timestamps,
and (best case) Arabic subtitles with word timings to slice 20:13 exactly.

Failure-transparent: ALWAYS writes recon.json + commits evidence (exit 0).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(".")
OUT_DIR = ROOT / "assets" / "quran" / "008_ta-ha_20-13_ghaith-samreen" / "audio_recon"
LOGS = OUT_DIR / "logs"

CANDIDATES: list[str] = [
    # oRVBNlJMQ7s ("Surah Taha - ... by Ghaith Samrin") is REMOVED by uploader (verified 2026-11-24).
    # IDs below recovered from aggregator thumbnail URLs (nogomi.ru, 2026-11-24).
    "https://www.youtube.com/watch?v=TkAp2_fKgsY",  # "Calmest Recitation Of Surat Taha ... 20 1 35" (3:29)
    "https://www.youtube.com/watch?v=dcH79-4KMf4",  # "سورة طه من صوت الشيخ غيث سمرين" (3:41)
]
SEARCHES = [
    "ytsearch8:Calmest Recitation Of Surat Taha By Ghaith Semreen 20 1 35",
    "ytsearch8:Ghaith Samreen Surah Taha recitation",
    "ytsearch8:غيث سمرين طه",
    "ytsearch8:Ghaith Semreen Quran recitation no effects",
]

recon: dict = {"status": "failed", "candidates": {}, "searches": {}}


def log(msg: str) -> None:
    print(f"[slot-008-audio-recon] {msg}", flush=True)


def capture(name: str, cmd: list[str]) -> tuple[int, str, str]:
    log("$ " + " ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = 124, str(e.stdout or ""), f"TIMEOUT 300s: {e}"
    except FileNotFoundError as e:
        rc, out, err = (127, "", f"NOT FOUND: {e}")
    (LOGS / f"{name}.out.txt").write_text(out[-20000:], encoding="utf-8")
    (LOGS / f"{name}.err.txt").write_text(err[-20000:], encoding="utf-8")
    return rc, out, err


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    for i, url in enumerate(CANDIDATES):
        tag = f"cand{i}"
        entry: dict = {"url": url}
        rc, out, err = capture(f"{tag}_dump",
            [sys.executable, "-m", "yt_dlp", "--no-playlist", "--skip-download",
             "--dump-single-json", url])
        entry["dump_rc"] = rc
        if rc == 0:
            try:
                meta = json.loads(out)
                (OUT_DIR / f"{tag}_meta.json").write_text(
                    json.dumps(meta, ensure_ascii=False, indent=1)[:200000], encoding="utf-8")
                entry.update({
                    "title": meta.get("title"), "duration": meta.get("duration"),
                    "uploader": meta.get("uploader"),
                    "chapters": meta.get("chapters"),
                    "description": (meta.get("description") or "")[:3000],
                    "subtitles": sorted((meta.get("subtitles") or {}).keys()),
                    "auto_captions": sorted((meta.get("automatic_captions") or {}).keys()),
                })
                # Grab Arabic subs/auto-subs if present (timestamps = exact slice!).
                for subkind, arg in (("sub", "--write-sub"), ("auto", "--write-auto-sub")):
                    if subkind == "sub" and not any("ar" in k for k in entry["subtitles"]):
                        continue
                    if subkind == "auto" and not any("ar" in k for k in entry["auto_captions"]):
                        continue
                    rc2, _, _ = capture(f"{tag}_{subkind}",
                        [sys.executable, "-m", "yt_dlp", "--no-playlist", "--skip-download",
                         "--sub-langs", "ar.*", arg, "--sub-format", "vtt",
                         "-o", str(OUT_DIR / f"{tag}_%(id)s.%(ext)s"), url])
                    entry[f"{subkind}_rc"] = rc2
            except json.JSONDecodeError:
                entry["dump_parse"] = "JSON-DECODE-FAIL"
        recon["candidates"][tag] = entry

    for j, query in enumerate(SEARCHES):
        tag = f"search{j}"
        rc, out, err = capture(tag,
            [sys.executable, "-m", "yt_dlp", "--no-playlist", "--flat-playlist",
             "--dump-single-json", query])
        entry = {"query": query, "rc": rc}
        if rc == 0:
            try:
                data = json.loads(out)
                (OUT_DIR / f"{tag}.json").write_text(
                    json.dumps(data, ensure_ascii=False, indent=1)[:100000], encoding="utf-8")
                entries = data.get("entries") or []
                entry["results"] = [
                    {"title": e.get("title"), "url": e.get("url"), "duration": e.get("duration"),
                     "uploader": e.get("uploader")}
                    for e in entries if isinstance(e, dict)
                ]
            except json.JSONDecodeError:
                entry["parse"] = "JSON-DECODE-FAIL"
        recon["searches"][tag] = entry

    ok = any(e.get("dump_rc") == 0 for e in recon["candidates"].values())
    recon["status"] = "success" if ok else "failed"
    (OUT_DIR / "recon.json").write_text(
        json.dumps(recon, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"recon {recon['status']}")


if __name__ == "__main__":
    main()
