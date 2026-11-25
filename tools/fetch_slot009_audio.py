#!/usr/bin/env python3
"""Slot 009 staging: Minshawi Murattal (QF 9) 3:193-197 mp3s + word timings.

Pure fetcher: resolves each ayah's audio_url via recitations/9/by_ayah,
downloads the mp3, probes duration, mirrors words=true&audio=9 timings.
Window selection (193 + next ayat to >=35 s) and assembly happen locally
after this report lands. Always writes report.json (exit 0 on success path,
raises + fetch_error.txt on hard failure like slot 007).
"""
from __future__ import annotations
import json, subprocess, time, traceback, urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (compatible; content-plug-quran-slot009/1.0)"
SLOT = "009_aal-e-imran_minshawi_staging"
ASSETS = Path(".") / "assets" / "quran" / SLOT
AYAHS = [193, 194, 195, 196, 197]
RECITER = 9

def log(m): print(f"[slot-009-audio] {m}", flush=True)

def _http(url, accept, timeout):
    last = None
    for a, w in ((1, 2.0), (2, 6.0), (3, 15.0)):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            log(f"WARN GET attempt {a}/3 failed {url}: {e}; sleep {w}s")
            time.sleep(w)
    raise last

def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    rep = {"status": "failed", "ayahs": []}
    for n in AYAHS:
        rec = json.loads(_http(
            f"https://api.quran.com/api/v4/recitations/{RECITER}/by_ayah/3:{n}",
            "application/json", 120).decode("utf-8"))
        (ASSETS / f"recit_3-{n}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(1.0)
        af = rec.get("audio_file") or (rec.get("audio_files") or [None])[0] or {}
        au = af.get("audio_url") or af.get("url")
        if not au:
            raise RuntimeError(f"3:{n}: no audio_url; top-level keys={list(rec.keys())}")
        if not au.startswith("http"):
            au = "https://audio.qurancdn.com/" + au.lstrip("/")
        mp3 = ASSETS / f"00319{n}.mp3"
        log(f"downloading 3:{n} {au}")
        mp3.write_bytes(_http(au, "*/*", 300))
        if mp3.stat().st_size < 5000:
            raise RuntimeError(f"3:{n} mp3 too small ({mp3.stat().st_size} B)")
        pr = json.loads(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size,bit_rate:stream=codec_name,sample_rate,channels",
             "-of", "json", str(mp3)], text=True))
        qf = json.loads(_http(
            f"https://api.quran.com/api/v4/verses/by_key/3:{n}?words=true&audio={RECITER}&word_fields=text_qpc_hafs",
            "application/json", 120).decode("utf-8"))
        (ASSETS / f"qf_3-{n}.json").write_text(
            json.dumps(qf, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(1.0)
        segs = qf["verse"]["audio"]["segments"]
        item = {"n": n, "url": au, "bytes": int(pr["format"]["size"]),
                "duration": round(float(pr["format"]["duration"]), 3),
                "first_ms": segs[0][2], "last_ms": segs[-1][3], "n_words": len(segs)}
        rep["ayahs"].append(item)
        log(f"3:{n}: {item['duration']} s, words {len(segs)}, span {segs[0][2]}-{segs[-1][3]} ms")
    tot, acc = 0.0, []
    for a in rep["ayahs"]:
        tot += a["duration"]
        acc.append(round(tot, 2))
    rep["accumulated_file_s"] = acc
    rep["status"] = "ok"
    (ASSETS / "report.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log("SUCCESS: 5 ayahs staged")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        ASSETS.mkdir(parents=True, exist_ok=True)
        tb = traceback.format_exc()
        (ASSETS / "fetch_error.txt").write_text(tb, encoding="utf-8")
        print(tb, flush=True)
        raise
