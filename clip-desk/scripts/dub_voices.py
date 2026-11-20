#!/usr/bin/env python3
"""Dub a script with one voice per character.

A localisation read is recorded per character, not per line: a single TTS call
per character sounds natural, but the lines then have to be recovered from the
recording before they can be placed on the timeline. This script does that
split, applies a character chain (pitch/formant/EQ) to each voice, and conforms
the result into the caption slots.

Each entry in the manifest is one recording that holds a known, ordered list of
script lines:

  {"file": "d1.mp3", "voice": "deep", "lines": [1, 2, 4]}

The recording is cut on silence, then the pieces are grouped into exactly
`len(lines)` parts by dynamic programming: it minimises the distance between
each part's end and the char-proportional target for its line, and pays a
penalty for swallowing a long pause, so a sentence break is never crossed by
accident. The best and the runner-up hypothesis are printed with their costs —
if the two are close, re-record that group instead of trusting it.

Voice chains come from the manifest's `voices` map (any ffmpeg -af chain), so a
character's timbre is one string: pitch and formant shifts to hit a target
pitch measured from the original performance, plus EQ and compression.

usage:
  dub_voices.py --script script.json --manifest voices.json --out vo.wav
"""

import argparse
import json
import os
import subprocess
import sys
import wave
from itertools import combinations

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import save_json, tool  # noqa: E402

FF = tool("ffmpeg")
SR = 48000


def decode(path, chain=None):
    cmd = [FF, "-v", "error", "-i", str(path)]
    if chain:
        cmd += ["-af", chain]
    cmd += ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed on {path}: {r.stderr.decode()[:400]}")
    return np.frombuffer(r.stdout, np.float32)


def atempo(x, factor):
    if abs(factor - 1.0) < 0.01:
        return x
    open("/tmp/_dv.raw", "wb").write(x.astype(np.float32).tobytes())
    out = subprocess.run([FF, "-y", "-v", "error", "-f", "f32le", "-ar", str(SR),
                          "-ac", "1", "-i", "/tmp/_dv.raw", "-filter:a",
                          f"atempo={factor:.4f}", "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(out, np.float32)


def chunks(x, hop=0.01, minpause=0.28, minspeech=0.12):
    """Speech islands, with pauses shorter than `minpause` treated as internal."""
    n = int(hop * SR)
    frames = len(x) // n
    if frames == 0:
        return []
    e = np.array([np.sqrt((x[i * n:(i + 1) * n] ** 2).mean()) for i in range(frames)])
    thr = max(e.max() * 0.04, np.percentile(e, 15) * 1.6, 1e-4)
    out, i = [], 0
    while i < frames:
        if e[i] > thr:
            j = last = i
            while j < frames:
                if e[j] > thr:
                    last = j
                elif (j - last) * hop > minpause:
                    break
                j += 1
            if (last - i + 1) * hop >= minspeech:
                out.append((i * hop, (last + 1) * hop))
            i = last + 1
        else:
            i += 1
    return out


def hypotheses(cs, want, weights, total, top=3):
    """Best `want` groupings of consecutive chunks, plus runners-up."""
    m = len(cs)
    if m < want:
        return [], f"{m} speech chunks for {want} lines"
    tgt = np.cumsum(weights)[:-1] * total
    scored = []
    for cuts in combinations(range(1, m), want - 1):
        bounds = (0,) + cuts + (m,)
        cost = 0.0
        for g in range(want - 1):
            cost += abs(cs[bounds[g + 1] - 1][1] - tgt[g])
        for g in range(want):                     # penalise crossing a long pause
            for k in range(bounds[g], bounds[g + 1] - 1):
                cost += 0.5 * (cs[k + 1][0] - cs[k][1])
        scored.append((cost, cuts))
    scored.sort()
    return scored[:top], None


def main():
    ap = argparse.ArgumentParser(description="One Arabic voice per character.")
    ap.add_argument("--script", required=True, help="caption script (ar/t0/t1)")
    ap.add_argument("--manifest", required=True, help="clips + voice chains")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tempo", type=float, default=1.30,
                    help="fastest a line may be squeezed to fit its slot")
    ap.add_argument("--gap", type=float, default=0.10,
                    help="minimum gap kept after a line (seconds)")
    args = ap.parse_args()

    lines = json.load(open(args.script, encoding="utf-8"))
    man = json.load(open(args.manifest, encoding="utf-8"))
    chains = {k: v.get("chain") for k, v in man.get("voices", {}).items()}
    base = os.path.dirname(os.path.abspath(args.manifest))

    pieces, weak = {}, []
    for clip in man["clips"]:
        idx = clip["lines"]
        voice = clip["voice"]
        x = decode(os.path.join(base, clip["file"]), chains.get(voice))
        if len(x) == 0:
            sys.exit(f"empty decode: {clip['file']}")
        cs = chunks(x)
        span = cs[-1][1] - cs[0][0] if cs else 0.0
        chars = np.array([max(1, len(lines[i]["ar"])) for i in idx], float)
        weights = list(chars / chars.sum())
        hyps, err = hypotheses(cs, len(idx), weights, span)
        if err:
            sys.exit(f"{clip['file']}: {err} — re-record this group split in two")
        picks = hyps[0][1]
        bounds = (0,) + picks + (len(cs),)
        margin = (hyps[1][0] - hyps[0][0]) if len(hyps) > 1 else 99.0
        if margin < 0.15:
            weak.append(clip["file"])
        print(f"{clip['file']} [{voice}] {len(cs)} chunks -> {len(idx)} lines  "
              f"cost {hyps[0][0]:.2f}  margin {margin:.2f}")
        for g, i in enumerate(idx):
            a, b = cs[bounds[g]][0], cs[bounds[g + 1] - 1][1]
            pieces[i] = (x[int(a * SR):int(b * SR)], voice)
            print(f"    line {i + 1:2d} {b - a:5.2f}s  {lines[i]['ar'][:44]}")
    if weak:
        print("WARNING: ambiguous groups:", ", ".join(weak))

    end = max(l["t1"] for l in lines) + 1.0
    buf = np.zeros((int(end * SR), 2), np.float32)
    cursor, problems = 0.0, []
    for i, (seg, voice) in sorted(pieces.items()):
        ln = lines[i]
        nxt = lines[i + 1]["t0"] if i + 1 < len(lines) else ln["t1"] + 0.6
        avail = max(ln["t1"], nxt) - ln["t0"]
        dur = len(seg) / SR
        f = dur / avail
        if f > 1.02:
            at = min(f, args.max_tempo)
            seg = atempo(seg, at)
            if f > args.max_tempo + 0.01:
                problems.append((i + 1, round(dur, 2), round(avail, 2)))
        start = max(ln["t0"], cursor)
        ln["t0_orig"], ln["t0"] = ln["t0"], round(start, 3)
        dur = len(seg) / SR
        ln["t1"] = round(max(start + dur, min(ln["t1"], start + dur + 0.25)), 3)
        ln["voice"] = voice
        cursor = start + dur + args.gap
        k = int(0.012 * SR)
        if len(seg) > 2 * k:
            seg = seg.copy()
            seg[:k] *= np.linspace(0, 1, k)
            seg[-k:] *= np.linspace(1, 0, k)
        st = int(ln["t0"] * SR)
        en = min(len(buf), st + len(seg))
        buf[st:en, 0] += seg[:en - st]
        buf[st:en, 1] += seg[:en - st]
        print(f"  line {i + 1:2d} {ln['t0']:5.1f}s  speech {dur:4.2f}s  "
              f"slot {avail:4.2f}s  {'ok' if f <= 1.02 else 'x%.2f' % min(f, args.max_tempo)}")
    if problems:
        print("overruns beyond max tempo:", problems)

    buf = buf / max(1.0, float(np.abs(buf).max()) / 0.95)
    with wave.open(args.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    conformed = os.path.splitext(args.out)[0] + "_script.json"
    save_json(conformed, lines)
    shift = max((abs(l["t0"] - l["t0_orig"]) for l in lines if "t0_orig" in l), default=0.0)
    print(f"wrote {args.out} {len(buf) / SR:.1f}s  max conform shift {shift:.2f}s")
    print(f"conformed script -> {conformed}")


if __name__ == "__main__":
    main()
