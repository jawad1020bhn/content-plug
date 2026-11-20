#!/usr/bin/env python3
"""Dub a script with one voice per character, without ever guessing where a
line ends.

Two placement modes, chose per recording:

  "split"  one recording holds several lines and they must be cut apart. The
           pieces are found on silence and grouped by dynamic programming whose
           cost compares each part with the char-proportional target and
           penalises swallowing a long pause. The best *and* runner-up costs are
           printed: a small margin means "re-record this as single lines".

  "block"  the recording holds lines whose cues are consecutive, so it is
           placed as one continuous take at the first cue and the captions are
           re-timed inside it by character share. Nothing is cut, so nothing can
           land under the wrong caption — at worst a caption starts a beat early.

Single-line recordings are just `"lines": [i]` (a `block` of one).

Each voice gets an ffmpeg chain, which is how a character is made: pitch and
formant shifts to hit a pitch measured from the original performance, then EQ
and compression so it still sounds like a person rather than a shifted file.

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
    """Speech islands; pauses shorter than `minpause` count as internal."""
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


def trim(x):
    """Drop leading/trailing silence so a block starts on the first syllable."""
    c = chunks(x, minpause=0.20, minspeech=0.05)
    if not c:
        return x
    return x[int(c[0][0] * SR):int(c[-1][1] * SR)]


def force_split(x, cs, want, hop=0.01):
    """Break the widest chunk at its quietest frame until there are `want`.

    Only used when the engine left no pause at all between short lines.
    """
    n = int(hop * SR)
    cs = [list(c) for c in cs]
    while len(cs) < want:
        cand = [k for k, (a, b) in enumerate(cs) if (b - a) > 0.30]
        if not cand:
            break
        widest = max(cand, key=lambda k: cs[k][1] - cs[k][0])
        a, b = cs[widest]
        lo, hi = int((a + 0.06) * SR), int((b - 0.06) * SR)
        if hi - lo < 2 * n:
            break
        e = np.array([np.sqrt((x[i:i + n] ** 2).mean()) for i in range(lo, hi, n)])
        cut = (lo + int(np.argmin(e)) * n) / SR
        cs[widest:widest + 1] = [[a, cut], [cut, b]]
    return [tuple(c) for c in cs]


def snap_to_min(x, t, window=0.45, hop=0.01):
    """Nearest quiet frame to `t` — where a real inter-word gap already exists."""
    n = int(hop * SR)
    lo = max(0, int((t - window) * SR))
    hi = min(len(x) - 2 * n, int((t + window) * SR))
    if hi <= lo:
        return t
    e = np.array([np.sqrt((x[i:i + n] ** 2).mean()) for i in range(lo, hi, n)])
    return (lo + int(np.argmin(e)) * n) / SR


def pick_chunks(x, want):
    """Longest pause threshold that still yields `want` chunks, else forced cuts."""
    fallback = None
    for mp in (0.30, 0.24, 0.18, 0.13, 0.09):
        cs = chunks(x, minpause=mp)
        if len(cs) >= want:
            return cs, mp
        if fallback is None or len(cs) > len(fallback):
            fallback = cs
    return force_split(x, fallback or [], want), 0.0


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
        for g in range(want):
            for k in range(bounds[g], bounds[g + 1] - 1):
                cost += 0.5 * (cs[k + 1][0] - cs[k][1])
        scored.append((cost, cuts))
    scored.sort()
    return scored[:top], None


def main():
    ap = argparse.ArgumentParser(description="One Arabic voice per character.")
    ap.add_argument("--script", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tempo", type=float, default=1.30,
                    help="fastest a line may be squeezed (dub standard is ~1.25)")
    ap.add_argument("--gap", type=float, default=0.08,
                    help="minimum silence kept after a unit (seconds)")
    ap.add_argument("--mode", default="split", choices=["split", "block"],
                    help="default mode for clips that do not declare one")
    ap.add_argument("--keep-caption-times", action="store_true",
                    help="never move a caption; only fit the audio into its slot")
    args = ap.parse_args()

    lines = json.load(open(args.script, encoding="utf-8"))
    man = json.load(open(args.manifest, encoding="utf-8"))
    chains = {k: v.get("chain") for k, v in man.get("voices", {}).items()}
    base = os.path.dirname(os.path.abspath(args.manifest))

    units, weak = [], []
    for clip in man["clips"]:
        idx, voice = clip["lines"], clip["voice"]
        mode = clip.get("mode", "block" if len(idx) > 1 else "split")
        x = decode(os.path.join(base, clip["file"]), chains.get(voice))
        if len(x) == 0:
            sys.exit(f"empty decode: {clip['file']}")

        if mode == "block":
            # One continuous take over consecutive cues: keep it intact, but cut
            # at a real pause near each estimated boundary so every line sits
            # under its own caption. Captions themselves are never moved.
            seg = trim(x)
            total = len(seg) / SR
            chars = np.array([max(1, len(lines[i]["ar"])) for i in idx], float)
            cum = np.cumsum(chars) / chars.sum() * total
            bounds, prev = [], 0.0
            for c in cum[:-1]:
                b = min(max(snap_to_min(seg, c), prev + 0.15), total - 0.15)
                bounds.append(b)
                prev = b
            edges = [0.0] + bounds + [total]
            print(f"{clip['file']} [{voice}] anchored block {len(idx)} lines  "
                  f"{total:.2f}s  cuts {[round(b, 2) for b in bounds]}")
            for g, i in enumerate(idx):
                units.append({"idx": [i],
                              "samples": seg[int(edges[g] * SR):int(edges[g + 1] * SR)],
                              "voice": voice, "kind": "single"})
            continue

        cs, mp = pick_chunks(x, len(idx))
        span = cs[-1][1] - cs[0][0] if cs else 0.0
        chars = np.array([max(1, len(lines[i]["ar"])) for i in idx], float)
        hyps, err = hypotheses(cs, len(idx), list(chars / chars.sum()), span)
        if err:
            sys.exit(f"{clip['file']}: {err} — record these lines one by one")
        bounds = (0,) + hyps[0][1] + (len(cs),)
        margin = (hyps[1][0] - hyps[0][0]) if len(hyps) > 1 else 99.0
        if margin < 0.15:
            weak.append(clip["file"])
        print(f"{clip['file']} [{voice}] {len(cs)} chunks (pause {mp:.2f}s) -> "
              f"{len(idx)} lines  cost {hyps[0][0]:.2f}  margin {margin:.2f}")
        for g, i in enumerate(idx):
            a, b = cs[bounds[g]][0], cs[bounds[g + 1] - 1][1]
            units.append({"idx": [i], "samples": x[int(a * SR):int(b * SR)],
                          "voice": voice, "kind": "single"})
    if weak:
        print("WARNING: ambiguous groups (re-record line by line):", ", ".join(weak))

    orig = [{"t0": l["t0"], "t1": l["t1"]} for l in lines]
    buf = np.zeros((int((max(l["t1"] for l in lines) + 1.0) * SR), 2), np.float32)
    cursor, problems = 0.0, []
    for u in sorted(units, key=lambda u: u["idx"][0]):
        idx = u["idx"]
        first, last = idx[0], idx[-1]
        start = max(orig[first]["t0"], cursor)
        if u["kind"] == "block":
            span = max(orig[last]["t1"] - orig[first]["t0"], 0.3)
        else:
            # the caption's own window: the plate was measured against the
            # English that lived exactly there, so the caption must not move
            span = max(orig[first]["t1"] - orig[first]["t0"], 0.3)
        seg = u["samples"]
        dur = len(seg) / SR
        if dur > span * 1.02:
            if dur / span > args.max_tempo + 0.01:
                problems.append((first + 1, round(dur, 2), round(span, 2)))
            seg = atempo(seg, min(dur / span, args.max_tempo))
            dur = len(seg) / SR
        k = int(0.012 * SR)
        if len(seg) > 2 * k:
            seg = seg.copy()
            seg[:k] *= np.linspace(0, 1, k)
            seg[-k:] *= np.linspace(1, 0, k)
        st = int(start * SR)
        en = min(len(buf), st + len(seg))
        buf[st:en, 0] += seg[:en - st]
        buf[st:en, 1] += seg[:en - st]

        if u["kind"] == "block":                # captions follow the take
            total = float(sum(max(1, len(lines[i]["ar"])) for i in idx))
            acc = 0.0
            for i in idx:
                a = start + dur * acc / total
                acc += max(1, len(lines[i]["ar"]))
                b = start + dur * acc / total
                lines[i].update(t0_orig=orig[i]["t0"], t0=round(a, 3),
                                t1=round(b, 3), voice=u["voice"])
        elif not args.keep_caption_times:
            lines[first].update(t0_orig=orig[first]["t0"], t0=round(start, 3),
                                t1=round(max(start + dur,
                                             min(orig[first]["t1"], start + dur + 0.25)), 3),
                                voice=u["voice"])
        else:
            lines[first].update(t0_orig=orig[first]["t0"], voice=u["voice"])
        cursor = start + dur + args.gap
        tag = f"block {idx[0] + 1}-{idx[-1] + 1}" if u["kind"] == "block" else f"line {first + 1:2d}"
        print(f"  {tag:>13} {start:5.2f}s  speech {dur:4.2f}s  span {span:4.2f}s"
              f"  {'ok' if dur <= span * 1.02 else 'x%.2f' % min(dur / span, args.max_tempo)}")
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
    print(f"wrote {args.out} {len(buf) / SR:.1f}s  max caption shift {shift:.2f}s")
    print(f"conformed script -> {conformed}")


if __name__ == "__main__":
    main()
