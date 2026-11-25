#!/usr/bin/env python3
"""Slot 008 Invidious recon: fetch Ghaith Samreen Taha audio via Invidious APIs.

YouTube direct extraction is bot-walled from runners. Invidious instances
proxy YouTube streams; query several for TkAp2_fKgsY (20:1-35) and dcH79-4KMf4,
take the best audio adaptiveFormat URL, HEAD-check it.

Failure-transparent: ALWAYS writes invid_recon.json (exit 0).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(".")
OUT_DIR = ROOT / "assets" / "quran" / "008_ta-ha_20-13_ghaith-samreen" / "audio_recon"

INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://iv.duti.dev",
    "https://inv.us.projectsegfau.lt",
    "https://pipedapi.adminforge.de",  # piped shape fallback (different path, tried anyway)
]
VIDEOS = ["TkAp2_fKgsY", "dcH79-4KMf4"]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def log(msg: str) -> None:
    print(f"[slot-008-invid-recon] {msg}", flush=True)


def curl_json(url: str, timeout: int = 40) -> dict | None:
    try:
        out = subprocess.run(
            ["curl", "-sSL", "--max-time", str(timeout), "-A", UA, url],
            capture_output=True, text=True, timeout=timeout + 10)
        if out.returncode == 0 and out.stdout.strip().startswith("{"):
            return json.loads(out.stdout)
        log(f"GET {url} rc={out.returncode} len={len(out.stdout)} head={out.stdout[:120]!r}")
    except Exception as e:
        log(f"GET {url} failed: {e}")
    return None


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {"status": "failed", "attempts": []}
    for inst in INSTANCES:
        for vid in VIDEOS:
            for path in (f"/api/v1/videos/{vid}", f"/streams/{vid}"):
                url = inst + path
                data = curl_json(url)
                attempt = {"endpoint": url, "ok": data is not None}
                if data:
                    fmts = data.get("adaptiveFormats") or data.get("audioStreams") or []
                    aud = [f for f in fmts if "audio" in str(f.get("type", "")).lower()
                           or f.get("audioQuality")]
                    if aud:
                        best = max(aud, key=lambda f: int(f.get("bitrate") or f.get("bitrate", 0) or 0))
                        au = best.get("url", "")
                        attempt.update({"audio_url_len": len(au),
                                        "audio_url_head": au[:160],
                                        "container": best.get("container"),
                                        "bitrate": best.get("bitrate")})
                        if au.startswith("http"):
                            report["status"] = "success"
                report["attempts"].append(attempt)
                if report["status"] == "success":
                    break
            if report["status"] == "success":
                break
        if report["status"] == "success":
            break
    (OUT_DIR / "invid_recon.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"invid recon {report['status']}")


if __name__ == "__main__":
    main()
