#!/usr/bin/env python3
"""Slot 008: import Ghaith Samreen Taha audio via working Invidious instance.

invidious.nerdvpn.de /api/v1/videos/ returned valid JSON for both Taha
candidates, so harvest its audio-bearing stream URLs (adaptive audio first,
formatStreams itag 22/18 fallback) and download the actual media on the
runner. Always writes a report JSON and commits whatever was fetched.
"""
import html
import json
import re
import subprocess
import urllib.request
from pathlib import Path

OUT = Path("assets/quran/008_ta-ha_20-13_ghaith-samreen/audio_recon")
RAW = OUT / "invid_raw"
API = "https://invidious.nerdvpn.de/api/v1/videos/"
IDS = ["TkAp2_fKgsY", "dcH79-4KMf4", "wCjxe_KHfq8", "_DKUKYc_QxE"]


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.status != 200:
                return None, "http %s" % r.status
            return json.loads(r.read().decode("utf-8", "replace")), None
    except Exception as e:  # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, str(e)[:160])


def pick_streams(d):
    cands = []
    for a in d.get("adaptiveFormats") or []:
        if "audio" in (a.get("type") or "") and a.get("url"):
            cands.append(("adaptive-%s" % a.get("itag"), a["url"]))
    for f in d.get("formatStreams") or []:
        if f.get("url"):
            cands.append(("format-%s" % f.get("itag"), f["url"]))
    # prefer adaptive audio, then itag 22, then 18, then anything
    def rank(k):
        k = k[0]
        if k.startswith("adaptive"):
            return 0
        if k == "format-22":
            return 1
        if k == "format-18":
            return 2
        return 3
    cands.sort(key=rank)
    return cands


def fetch_captions(d, vid):
    """Download best caption track; hunt cue containing 20:13 keywords."""
    caps = d.get("captions") or []
    def rank(c):
        lab = (c.get("label") or "").lower()
        code = c.get("languageCode") or ""
        s = 0
        if code.startswith("ar"):
            s += 10
        if "auto" in lab:
            s += 5
        if code.startswith("en"):
            s += 1
        return -s
    for c in sorted(caps, key=rank)[:2]:
        url = c.get("url") or ""
        if url.startswith("/"):
            url = "https://invidious.nerdvpn.de" + url
        if not url:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                xml = r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        (RAW / ("%s.caps.xml" % vid)).write_text(xml)
        cues = re.findall(r'<p[^>]*t="(\d+)"[^>]*d="(\d+)"[^>]*>(.*?)</p>', xml, re.S)
        texts = [(int(t) / 1000.0, re.sub(r"<[^>]+>", "", html.unescape(x)))
                 for t, _dd, x in cues]
        hits = [(t, x[:90]) for t, x in texts
                if "اخترت" in x or "اختار" in x or "يوح" in x]
        return {"track": c.get("label"), "n_cues": len(texts),
                "hits": hits[:6],
                "head": " | ".join(x[:50] for _, x in texts[:8])}
    return {}


def download(url, dest):
    try:
        p = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "240", "-o", str(dest), url],
            capture_output=True, text=True, timeout=280)
        if p.returncode == 0 and dest.exists() and dest.stat().st_size > 100_000:
            return True, None
        return False, (p.stderr or "small/empty file")[:160]
    except Exception as e:  # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, str(e)[:160])


def probe(path):
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60)
        d = json.loads(p.stdout or "{}").get("format", {})
        return {"duration": d.get("duration"), "bytes": d.get("size")}
    except Exception:  # noqa: BLE001
        return {"duration": None, "bytes": path.stat().st_size}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    report = {"status": "failed", "items": []}
    for vid in IDS:
        item = {"id": vid}
        d, err = get_json(API + vid)
        if d is None:
            # retry with local=true (instance-proxied URLs)
            d, err2 = get_json(API + vid + "?local=true")
            err = err2 if d else err
        if d is None:
            item["ok"] = False
            item["error"] = err
            report["items"].append(item)
            print("FAIL api", vid, err, flush=True)
            continue
        item["title"] = (d.get("title") or "")[:120]
        item["length"] = d.get("lengthSeconds")
        item["captions"] = fetch_captions(d, vid)
        streams = pick_streams(d)
        item["n_streams"] = len(streams)
        got = None
        for label, url in streams[:6]:
            dest = RAW / ("%s_%s.mp4" % (vid, label.replace("-", "")))
            ok, derr = download(url, dest)
            print(("GOT " if ok else "miss ") + vid + " " + label,
                  str(dest.stat().st_size) if ok else derr, flush=True)
            if ok:
                got = {"file": str(dest), "via": label, **probe(dest)}
                break
            dest.unlink(missing_ok=True)
        item["ok"] = got is not None
        if got:
            item.update(got)
        else:
            item["error"] = "all stream downloads failed"
        report["items"].append(item)
    if any(i.get("ok") for i in report["items"]):
        report["status"] = "ok"
    (OUT / "invid_import.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False))
    print("IMPORT-REPORT-STATUS:", report["status"])


if __name__ == "__main__":
    main()
