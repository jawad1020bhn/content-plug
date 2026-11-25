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
APIS = [
    "https://yt.chocolatemoo53.com",
    "https://inv.thepixora.com",
    "https://invidious.nerdvpn.de",
    "https://inv.nadeko.net",
]
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


def fetch_captions(d, vid, base):
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
            url = base + url
        if not url:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                xml = r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        (RAW / ("%s.caps.xml" % vid)).write_text(xml)
        texts = []
        if xml.lstrip().startswith("WEBVTT"):
            for m in re.finditer(r"(\d+):(\d+):([\d.]+) --> [^\n]*\n(.*?)(?=\n\n|\Z)",
                                 xml, re.S):
                h, mi, se, body = m.groups()
                t = int(h) * 3600 + int(mi) * 60 + float(se)
                texts.append((t, re.sub(r"<[^>]+>", "", body).replace("\n", " ").strip()))
        else:
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
            ["curl", "-sS", "-L", "-A", "Mozilla/5.0", "--max-time", "240",
             "-o", str(dest), "-w", "code=%{http_code} size=%{size_download}", url],
            capture_output=True, text=True, timeout=280)
        meta = (p.stdout or "").strip()
        if p.returncode == 0 and dest.exists() and dest.stat().st_size > 100_000:
            return True, meta
        head = ""
        try:
            head = dest.read_bytes()[:200].decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            pass
        return False, "%s rc=%d err=%s head=%s" % (
            meta, p.returncode, (p.stderr or "")[:80], head[:160])
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
        d, err, base = None, None, None
        for b in APIS:
            d, err = get_json(b + "/api/v1/videos/" + vid)
            if d is None:
                d, err = get_json(b + "/api/v1/videos/" + vid + "?local=true")
            if d is not None:
                base = b
                break
        item["api"] = base
        if d is None:
            item["ok"] = False
            item["error"] = err
            report["items"].append(item)
            print("FAIL api", vid, err, flush=True)
            continue
        item["title"] = (d.get("title") or "")[:120]
        item["length"] = d.get("lengthSeconds")
        item["captions"] = fetch_captions(d, vid, base)
        d_local, _ = get_json(base + "/api/v1/videos/" + vid + "?local=true")
        streams = ([("L:" + k, u) for k, u in pick_streams(d_local)] if d_local else []) + \
            [("P:" + k, u) for k, u in pick_streams(d)]
        item["n_streams"] = len(streams)
        got, dl_errors = None, []
        for label, url in streams[:8]:
            dest = RAW / ("%s_%s.mp4" % (vid, label.replace(":", "").replace("-", "")))
            ok, derr = download(url, dest)
            print(("GOT " if ok else "miss ") + vid + " " + label,
                  str(dest.stat().st_size) if ok else derr, flush=True)
            if ok:
                got = {"file": str(dest), "via": label, **probe(dest)}
                break
            dl_errors.append({"stream": label, "err": derr})
            dest.unlink(missing_ok=True)
        item["dl_errors"] = dl_errors
        item["ok"] = got is not None
        if got:
            item.update(got)
        else:
            item["error"] = "all stream downloads failed"
        report["items"].append(item)
    if any(i.get("ok") for i in report["items"]):
        report["status"] = "ok"
    report["piped"] = []
    if report["status"] == "failed":
        for host in ["https://pipedapi.reallyaweso.me", "https://pipedapi.leptons.xyz",
                     "https://api-piped.mha.fi", "https://pipedapi.r4fo.com",
                     "https://pipedapi.adminforge.de"]:
            d, err = get_json(host + "/streams/TkAp2_fKgsY")
            entry = {"host": host, "ok": False}
            if d is None:
                entry["error"] = err
            else:
                aud = [a for a in (d.get("audioStreams") or []) if a.get("url")]
                entry["n_audio"] = len(aud)
                if aud:
                    aud.sort(key=lambda a: a.get("bitrate") or 0, reverse=True)
                    dest = RAW / "TkAp2_piped.m4a"
                    ok, derr = download(aud[0]["url"], dest)
                    entry["ok"] = ok
                    entry["detail"] = (str(dest.stat().st_size) if ok else derr)
                    if ok:
                        entry.update(probe(dest))
                        report["status"] = "piped-ok"
                        report["piped"].append(entry)
                        break
                    dest.unlink(missing_ok=True)
            report["piped"].append(entry)
            print("PIPED", host, entry.get("ok"),
                  entry.get("error") or entry.get("detail"), flush=True)
    (OUT / "invid_import.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False))
    print("IMPORT-REPORT-STATUS:", report["status"])


if __name__ == "__main__":
    main()
