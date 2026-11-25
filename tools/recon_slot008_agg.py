#!/usr/bin/env python3
"""Slot 008 aggregator recon: find direct Ghaith Samreen Taha mp3 downloads.

YouTube extraction is bot-walled from runners. These aggregator pages offer
"download mp3" for his Taha recitations; scrape their HTML for direct audio
file URLs (mp3 / googlevideo / download endpoints) and HEAD-check them.

Failure-transparent: ALWAYS writes agg_recon.json (exit 0).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(".")
OUT_DIR = ROOT / "assets" / "quran" / "008_ta-ha_20-13_ghaith-samreen" / "audio_recon"

PAGES = {
    "nogomi": "https://xn-----7sdda0a3ber1e6dxawp8cf.nogomi.ru/",
    "almleka": "https://xn--------ychrabdischbm9bv1ao0a5a9ik0xwaqmo0axl7bf.almleka.com/",
    "shabakngy": "https://xn-------64f9a4a5bdemj8b8byh5aa1audcr4df.shabakngy.com/",
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def log(msg: str) -> None:
    print(f"[slot-008-agg-recon] {msg}", flush=True)


def curl_html(url: str) -> str | None:
    try:
        out = subprocess.run(
            ["curl", "-sSL", "--max-time", "60", "-A", UA, url],
            capture_output=True, text=True, timeout=90)
        if out.returncode == 0 and len(out.stdout) > 5000:
            return out.stdout
        log(f"curl {url} rc={out.returncode} len={len(out.stdout)}")
    except Exception as e:
        log(f"curl {url} failed: {e}")
    return None


def head_check(url: str) -> dict:
    try:
        out = subprocess.run(
            ["curl", "-sSI", "--max-time", "30", "-A", UA, url],
            capture_output=True, text=True, timeout=60)
        hdr = out.stdout
        m_len = re.search(r"(?im)^content-length:\s*(\d+)", hdr)
        m_typ = re.search(r"(?im)^content-type:\s*([^\r\n;]+)", hdr)
        return {"head_rc": out.returncode,
                "content_type": (m_typ.group(1).strip() if m_typ else None),
                "content_length": (int(m_len.group(1)) if m_len else None)}
    except Exception as e:
        return {"head_rc": -1, "error": str(e)[:200]}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {"status": "failed", "pages": {}}
    for tag, url in PAGES.items():
        entry: dict = {"url": url, "candidates": []}
        html = curl_html(url)
        if html is None:
            entry["fetch"] = "FAILED"
            report["pages"][tag] = entry
            continue
        entry["fetch"] = f"OK {len(html)} bytes"
        (OUT_DIR / f"agg_{tag}.html").write_text(html[:300000], encoding="utf-8")
        # Candidate download/audio URLs: href/src attrs mentioning mp3, download,
        # googlevideo, videoplayback, or /dl|/down|/get- endpoints.
        urls = set(re.findall(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', html, re.I))
        cands = [u for u in urls if re.search(
            r"\.mp3|googlevideo|videoplayback|download|/dl/|/down|get\.|audio", u, re.I)]
        # Resolve relative URLs crudely.
        base = re.match(r"(https?://[^/]+)", url).group(1)
        cands = [u if u.startswith("http") else (base + u if u.startswith("/") else u)
                 for u in cands]
        seen = set()
        for u in cands:
            if u in seen or len(entry["candidates"]) >= 12:
                continue
            seen.add(u)
            info = {"url": u[:400]}
            if u.startswith("http"):
                info.update(head_check(u))
            entry["candidates"].append(info)
        report["pages"][tag] = entry
    ok = any(any((c.get("content_type") or "").startswith("audio")
                  or (c.get("content_length") or 0) > 500000
                  for c in p.get("candidates", []))
             for p in report["pages"].values())
    report["status"] = "success" if ok else "failed"
    (OUT_DIR / "agg_recon.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"agg recon {report['status']}")


if __name__ == "__main__":
    main()
