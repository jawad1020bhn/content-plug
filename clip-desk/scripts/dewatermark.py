"""Remove a burned-in watermark from a video you own or have licensed.

usage: python dewatermark.py <in.mp4> --out <out.mp4> --rights own|licensed
                             [--mode matte|soft|delogo|crop] [mode options]
                             [--calibrate auto|t:x,y,w,h] [--probe 12]
                             [--preview 6] [--crf 18] [--force]
       python dewatermark.py --probe 12 <in.mp4>      # where is the mark?
       python dewatermark.py --selftest               # is the engine sane?

Modes
  matte   (default) Semi-transparent marks. Calibrates the mark's alpha and
          white level from one frame where it sits on a plain background, then
          tracks it per frame by matched filter and subtracts its fitted
          per-channel contribution. Restores the background instead of smearing
          a patch over it. Frames where the mark is not found pass through (or
          get the soft pass, with --soft-on-miss).
  soft    No detection. Suppresses LOW-AMPLITUDE brightening everywhere, which
          fades a pale overlay but also flattens faint highlights. Use when the
          mark moves too much to track.
  delogo  ffmpeg's delogo on a fixed box (--box x,y,w,h). For opaque, static
          logos or text. Fast, but interpolates from the box edges.
  crop    Reframes so an edge band is cut away (--crop 200 = drop 200px), then
          scales back up. Clean removal when the mark hugs one edge.

Repeat runs should start with --probe: it samples the video, reports recurring
pale text-like shapes, and prints a calibration box *that it has verified*
against the overlay model. --calibrate auto does that inside a normal run.

Nothing here posts, uploads or credits anything. --rights is required to process
and lands in the sidecar JSON: a clip whose attribution status is unrecorded
never enters the pipeline. Only use this on footage you own or licensed --
removing someone else's watermark is attribution stripping, not editing.

Every run writes a before/after sheet so a human can approve the result.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import tool, ffprobe, save_json

import cv2
import numpy as np


# ---------------------------------------------------------------- ffmpeg I/O
def video_info(path):
    meta = ffprobe(path)
    vs = [s for s in meta["streams"] if s["codec_type"] == "video"]
    if not vs:
        sys.exit(f"no video stream in {path}")
    v = vs[0]
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1)
    dur = float(meta["format"]["duration"])
    has_audio = any(s["codec_type"] == "audio" for s in meta["streams"])
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": fps,
            "dur": dur, "audio": has_audio, "frames": int(round(dur * fps))}


def encode(frames_iter, info, src, out, crf):
    """Pipe BGR frames into x264 and keep the source audio untouched."""
    cmd = [tool("ffmpeg"), "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{info['w']}x{info['h']}", "-r", f"{info['fps']:.6f}",
           "-i", "-", "-i", str(src),
           "-map", "0:v:0", "-map", "1:a:0?" if info["audio"] else "1:a:0",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", str(out)]
    if not info["audio"]:
        cmd = [c for c in cmd if c not in ("-map", "1:a:0") and c != "-c:a"]
        cmd = [c for c in cmd if c != "copy"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in frames_iter:
            p.stdin.write(f.tobytes())
    finally:
        p.stdin.close()
        rc = p.wait()
    if rc != 0:
        sys.exit(f"ffmpeg encode failed ({rc})")


def iter_frames(src, info):
    cap = cv2.VideoCapture(str(src))
    n = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        yield fr
    cap.release()
    if n == 0:
        sys.exit(f"decoded 0 frames from {src}")


# ------------------------------------------------------------------ helpers
def gray(fr):
    return cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr


def local_bg(g, window):
    """Smooth background estimate, cheap: median at 1/4 scale then upscale."""
    sc = 0.25
    small = cv2.resize(g, (0, 0), fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    k = max(3, int(window * sc) | 1)
    med = cv2.medianBlur(small, k)
    return cv2.resize(med, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_LINEAR)


def suppress_soft(fr, window, t1, t2):
    """Fade low-amplitude brightening (= pale overlay) without touching real edges."""
    lab = cv2.cvtColor(fr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[:, :, 0]
    bg = local_bg(L.astype(np.uint8), window).astype(np.float32)
    r = L - bg
    keep = np.where(r > 0, np.clip((np.abs(r) - t1) / max(t2 - t1, 1e-6), 0, 1), 1.0)
    lab[:, :, 0] = np.clip(bg + r * keep, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def plane_bg(patch, trim=68, iters=3):
    """Smooth quadratic backdrop fitted to a patch, ignoring the bright mark.

    A wide median is only trustworthy when the patch is flat and far from the
    frame edge; elsewhere it biases the fit and alpha comes out negative. Fitting
    a surface and repeatedly trimming the brightest pixels is stable in both
    cases, and finds the mark by construction.
    """
    h, w = patch.shape
    u = (np.arange(w, dtype=np.float64) / max(w - 1, 1))[None, :].repeat(h, 0)
    v = (np.arange(h, dtype=np.float64) / max(h - 1, 1))[:, None].repeat(w, 1)
    A = np.stack([np.ones_like(u), u, v, u * u, u * v, v * v], -1).reshape(-1, 6)
    y = patch.astype(np.float64).reshape(-1)
    keep = np.ones(y.shape, bool)
    coef = np.zeros(6)
    for _ in range(iters):
        if keep.sum() < 20:
            break
        coef, *_ = np.linalg.lstsq(A[keep], y[keep], rcond=None)
        r = y - A @ coef
        keep = r <= np.percentile(r, trim)
    return (A @ coef).reshape(h, w)


def calibrate(src, spec, max_px=80000):
    """Estimate the mark's alpha and white level from one sample.

    spec = "t:x,y,w,h" -- a timestamp where the whole mark sits on a plain area.
    Model: I = (1-a)B + aW, with B from a robust surface fit. Raises ValueError
    when the box cannot be explained by that model, so callers can try another
    candidate instead of shipping a confident wrong calibration.
    """
    t, box = spec.split(":", 1)
    x, y, w, h = (int(v) for v in box.split(","))
    cap = cv2.VideoCapture(str(src))
    cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000.0)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        raise ValueError(f"could not read a frame at {t}s")

    g = gray(fr).astype(np.float64)
    H, W = g.shape
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 - x0 < 40 or y1 - y0 < 10:
        raise ValueError("box too small")
    sub = g[y0:y1, x0:x1]
    if sub.shape[0] * sub.shape[1] > max_px:            # keep calibration fast
        f = int(np.sqrt(sub.shape[0] * sub.shape[1] / max_px)) or 2
        sub = sub[::f, ::f]

    B = plane_bg(sub)
    d = sub - B
    keep = d > max(np.percentile(d, 82), 4)
    if keep.sum() < 40:
        raise ValueError("no pale mark found in that box")

    if np.ptp(B[keep]) > 15:
        # enough background variation to separate alpha from the white level
        A = np.stack([B[keep], np.ones(int(keep.sum()))], 1)
        (slope, icept), *_ = np.linalg.lstsq(A, sub[keep], rcond=None)
        alpha = 1.0 - slope
        white = icept / alpha if abs(alpha) > 1e-3 else float("nan")
    else:
        # flat backdrop: assume a white overlay (the common case), solve alpha
        white = 255.0
        alpha = float(np.median(d[keep] / np.maximum(white - B[keep], 1.0)))

    if not (0.02 < alpha < 0.95) or not (60 < white <= 300):
        raise ValueError(f"implausible fit (alpha={alpha:.2f}, white={white:.0f})")

    resid = float(np.sqrt(np.mean((sub[keep] - ((1 - alpha) * B[keep] + alpha * white)) ** 2)))
    if resid > 9.0:
        raise ValueError(f"poor fit (residual {resid:.1f})")

    den = white - B
    matte = np.where(den > 10, np.clip(d / np.maximum(den, 1.0), 0, 1), 0.0)
    ys, xs = np.where(matte > 0.02)
    if len(xs) < 50:
        raise ValueError("mark vanished during matte build")
    matte = matte[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    origin = (x0 + int(xs.min()), y0 + int(ys.min()))
    return {"alpha": float(alpha), "white": float(white), "resid": resid,
            "matte": matte.astype(np.float32), "origin": origin}


def unblend(fr, box, cal):
    """Remove the mark's own contribution from the pixels it covers.

    The matte gives the overlay's *shape*. Its amplitude depends on the
    background (I = (1-a)B + aW, so it is a(W-B) per channel), which is why a
    single global alpha over- or under-corrects. Instead we fit the matte's
    amplitude per channel for this frame against a smooth backdrop and subtract
    it. Fitting that backdrop explicitly means the text can no longer bias the
    background estimate, which a wide median does when the mark is large.
    """
    x, y = box
    mat = cal["matte"]
    h, w = mat.shape
    H, Wd = fr.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, Wd), min(y + h, H)
    if x1 - x0 < 8 or y1 - y0 < 4:
        return fr
    mm = mat[y0 - y:y1 - y, x0 - x:x1 - x]
    if mm.max() <= 0.02:
        return fr
    sub = fr[y0:y1, x0:x1].astype(np.float32)
    hh, ww = mm.shape
    u = (np.arange(ww, dtype=np.float32) / max(ww - 1, 1))[None, :].repeat(hh, 0)
    v = (np.arange(hh, dtype=np.float32) / max(hh - 1, 1))[:, None].repeat(ww, 1)
    A = np.stack([mm, np.ones_like(mm), u, v, u * u, u * v, v * v], -1).reshape(-1, 7)
    out = fr.copy()
    for c in range(sub.shape[2]):
        yv = sub[:, :, c].reshape(-1)
        coef, *_ = np.linalg.lstsq(A, yv, rcond=None)
        k = max(float(coef[0]), 0.0)               # the mark only ever brightens
        out[y0:y1, x0:x1, c] = np.clip(yv - k * mm.reshape(-1),
                                       0, 255).reshape(hh, ww).astype(np.uint8)
    return out


def mark_energy(fr, box, mat):
    """How much mark-like residue is left: bright bump plus dark over-correction."""
    x, y = box
    h, w = mat.shape
    H, Wd = fr.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, Wd), min(y + h, H)
    if x1 - x0 < 8 or y1 - y0 < 4:
        return None
    sub = gray(fr[y0:y1, x0:x1]).astype(np.float32)
    bg = local_bg(sub.astype(np.uint8), 61).astype(np.float32)
    d = sub - bg
    hi = float(np.percentile(d, 99.0))
    lo = float(np.percentile(d, 1.0))
    return hi - 1.5 * min(lo, 0.0)          # dark over-correction costs more than a ghost


def make_template(cal):
    t = cal["matte"] - cal["matte"].mean()
    n = np.linalg.norm(t)
    return (t / n if n else t).astype(np.float32)


def detect(g, tpl, cal, min_score, min_ratio):
    """Matched filter on the background-subtracted frame; returns (x, y, score)."""
    bg = cv2.medianBlur(g, 81).astype(np.float32)
    r = g.astype(np.float32) - bg
    R = cv2.matchTemplate(r, tpl, cv2.TM_CCOEFF_NORMED)
    _, s1, _, loc = cv2.minMaxLoc(R)
    m = R.copy()
    cv2.circle(m, loc, max(40, tpl.shape[1] // 3), float(R.min() - 1), -1)
    s2 = cv2.minMaxLoc(m)[1]
    if s1 < min_score or s1 / max(s2, 1e-6) < min_ratio:
        return None, s1
    # the template is the matte cropped to its bbox, so the match location is
    # already the mark's top-left in frame coordinates
    return (int(loc[0]), int(loc[1])), s1


# ------------------------------------------------------- discovery (the probe)
def find_candidates(g, max_n=6):
    """Pale text-line candidates in one frame.

    A watermark is lighter than its wide-median background, shaped like a line of
    text, and LOW contrast. That ceiling is what keeps bold captions and white
    artwork out of the list: they are near-white, so their mean lift is 30+.
    """
    d = g.astype(np.float32) - cv2.medianBlur(g, 81).astype(np.float32)
    m = (d > 4).astype(np.uint8)
    # gentle closing: aggressive kernels weld the mark onto nearby artwork and
    # the merged blob then fails the size test
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((2, 9), np.uint8))
    m = cv2.dilate(m, np.ones((2, 3), np.uint8), 1)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    H, W = g.shape
    out = []
    for i in range(1, n):
        x, y, w, h, _ = stats[i]
        if not (80 < w < 700 and 9 < h < 60) or w / max(h, 1) < 3.5:
            continue
        amp = float(d[lab == i].mean())
        if not (2.5 < amp < 30):
            continue
        fill = float((lab[y:y + h, x:x + w] == i).mean())
        if fill < 0.10:               # a text line is dense inside its box
            continue
        x0, y0 = max(x - 6, 0), max(y - 6, 0)
        x1, y1 = min(x + w + 6, W), min(y + h + 6, H)
        patch = g[y0:y1, x0:x1]
        out.append({"t": None, "box": (x0, y0, x1 - x0, y1 - y0),
                    "amp": amp, "flat": float(patch.std()), "px": int(w * h)})
    out.sort(key=lambda c: -c["px"])              # biggest text-like thing first
    return out[:max_n]


def probe(src, info, n=12, sheet=None):
    """Sample the video, report pale text-like marks, suggest a VERIFIED box.

    This is the step that should never be redone by hand. A real watermark
    recurs -- the same text-like shape at the same size, frame after frame -- so
    candidates are grouped by size and ranked by recurrence. Each proposed box is
    then fitted to I = (1-a)B + aW; only a box that passes that fit is suggested.
    """
    times = [info["dur"] * (i + 0.5) / n for i in range(n)]
    cap = cv2.VideoCapture(str(src))
    rows, tiles = [], []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, fr = cap.read()
        if not ok:
            continue
        cands = find_candidates(gray(fr))
        vis = fr.copy()
        for k, c in enumerate(cands[:3]):
            x, y, w, h = c["box"]
            cv2.rectangle(vis, (x, y), (x + w, y + h),
                          (0, 0, 255) if k == 0 else (0, 180, 255), 2)
        cv2.putText(vis, f"{t:.0f}s", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        for k, c in enumerate(cands[:3]):
            if k == 0 or c["px"] > 0.5 * cands[0]["px"]:
                rows.append(dict(c, t=round(t, 2)))
        sc = 260.0 / fr.shape[1]
        tiles.append(cv2.resize(vis, (260, int(fr.shape[0] * sc))))
    cap.release()

    groups = {}
    for c in rows:                       # group by size: the same mark, wherever it sits
        _, _, w, h = c["box"]
        groups.setdefault((round(w / 24.0), round(h / 8.0)), []).append(c)
    ranked = sorted(groups.values(),
                    key=lambda g: (len(g), max(c["px"] for c in g)), reverse=True)

    if ranked:
        print(f"{'n':>3} {'w x h':>9} {'amp':>5} {'flat':>5}  timestamps")
        for g in ranked[:6]:
            w = int(np.median([c["box"][2] for c in g]))
            h = int(np.median([c["box"][3] for c in g]))
            print(f"{len(g):3d} {w:4d} x{h:3d} "
                  f"{float(np.median([c['amp'] for c in g])):5.1f} "
                  f"{float(np.median([c['flat'] for c in g])):5.1f}  "
                  f"{[c['t'] for c in g][:8]}")
    else:
        print("no pale text-like shape found. Try --probe 24, or the mark may be opaque "
              "-> use --mode delogo --box x,y,w,h.")

    if sheet and tiles:
        rs = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
        wmax = max(r.shape[1] for r in rs)
        rs = [np.hstack([r, np.zeros((r.shape[0], wmax - r.shape[1], 3), np.uint8)]) for r in rs]
        cv2.imwrite(str(sheet), np.vstack(rs))
        print(f"sheet: {sheet}")

    widths = sorted({int(round(np.median([c["box"][2] for c in g])) / 50.0) * 50
                     for g in ranked if len(g) >= 2})
    if len(widths) > 1:
        print(f"note: {len(widths)} recurring mark sizes {widths} -- the mark is scaled per "
              "shot. One calibration fits one size; run per section to cover them all.")

    # verify each candidate against the overlay model; the first that fits wins
    tried = 0
    for group in ranked:
        for site in sorted(group, key=lambda c: (c["flat"], -c["px"])):
            x, y, w, h = site["box"]
            spec = f"{site['t']}:{x},{y},{w},{h}"
            tried += 1
            if tried > 8:
                break
            try:
                cal = calibrate(src, spec)
            except ValueError:
                continue
            if cal["alpha"] > 0.75:
                # a fitted alpha near 1 means opaque text (a caption or a solid
                # logo). That is delogo territory, not a pale overlay, and
                # un-blending it would paint over real content.
                continue
            print(f"verified: --calibrate {spec}  "
                  f"(alpha={cal['alpha']:.2f}, white={cal['white']:.0f}, residual {cal['resid']:.1f})")
            return spec
        if tried > 8:
            break
    if ranked:
        print("no pale candidate passed the overlay fit (opaque text is rejected here -- use "
              "--mode delogo for that). The sheet shows what was found; pick a frame where the "
              "whole mark sits on a plain background and pass --calibrate t:x,y,w,h yourself.")
    return None


def auto_calibrate(src, info, n=12):
    """Probe for a calibration box that passes the model check, or explain why not."""
    spec = probe(src, info, n)
    if not spec:
        sys.exit("could not verify a calibration box. Look at the probe sheet, then pass "
                 "--calibrate t:x,y,w,h for a frame where the whole mark sits on a plain area.")
    return spec


def selftest():
    """End-to-end check on a synthetic clip carrying a known 25%-alpha white mark.

    No fixture file needed: if this fails the removal engine is broken, whatever
    a real video happens to look like. Also checks that a bold caption is left
    alone -- the failure mode that matters.
    """
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="dewm_selftest_"))
    clip = tmp / "wm.mp4"
    W, H, FPS, N = 320, 480, 15, 45
    mark = (10, 372, 250, 46)             # x,y,w,h around the synthetic mark
    cap_box = (5, 40, 250, 45)
    cmd = [tool("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(clip)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(N):
        bg = np.zeros((H, W, 3), np.uint8)
        bg[:] = (150, 120 + int(60 * i / N), 60)
        cv2.circle(bg, (70 + i * 3, 150 + i * 2), 45, (60, 60, 210), -1)
        bg = cv2.GaussianBlur(bg, (0, 0), 11)
        cv2.putText(bg, "BOLD CAPTION", (12, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                    (255, 255, 255), 2, cv2.LINE_AA)
        ov = bg.copy()
        cv2.putText(ov, "@oldhandle", (16, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 255), 2, cv2.LINE_AA)
        p.stdin.write(cv2.addWeighted(ov, 0.25, bg, 0.75, 0).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        sys.exit("selftest: could not build the synthetic clip")

    info = video_info(clip)
    cap = cv2.VideoCapture(str(clip))
    cap.set(cv2.CAP_PROP_POS_MSEC, 1000.0 * 20 / FPS)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        sys.exit("selftest: could not read the synthetic clip")

    def amp(frame):
        g = gray(frame)
        x, y, w, h = mark
        sub = g[y:y + h, x:x + w].astype(np.float32)
        bg = local_bg(sub.astype(np.uint8), 41).astype(np.float32)
        return float(np.mean(np.clip(sub - bg, 0, None)))

    spec = auto_calibrate(clip, info)
    try:
        cal = calibrate(clip, spec)
    except ValueError as e:
        print(f"SELFTEST FAIL: calibration rejected the synthetic mark too ({e})")
        return False
    box, _ = detect(gray(fr), make_template(cal), cal, 0.2, 1.0)
    if box is None:
        print("SELFTEST FAIL: mark not located in the synthetic clip")
        return False
    out = unblend(fr, box, cal)

    a0, a1 = amp(fr), amp(out)
    x, y, w, h = cap_box
    guard = float(np.mean(np.abs(fr[y:y + h, x:x + w].astype(np.int16) -
                                 out[y:y + h, x:x + w].astype(np.int16))))
    ok_removal = a1 < 0.45 * a0
    ok_guard = guard < 3.0
    print(f"SELFTEST  mark amplitude {a0:.1f} -> {a1:.1f} "
          f"({100 * (1 - a1 / max(a0, 1e-6)):.0f}% removed)   caption drift {guard:.2f}")
    print("SELFTEST PASS" if (ok_removal and ok_guard) else
          f"SELFTEST FAIL (removal ok={ok_removal}, frame untouched ok={ok_guard})")
    return ok_removal and ok_guard


# ------------------------------------------------------------------ preview
def preview(src, out, info, cal, times, path):
    """Before/after sheet at the given timestamps so a human can approve."""
    tiles = []
    for t in times:
        cap = cv2.VideoCapture(str(src))
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, before = cap.read()
        cap.release()
        if not ok:
            continue
        cap = cv2.VideoCapture(str(out))
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, after = cap.read()
        cap.release()
        if not ok:
            continue
        h, w = before.shape[:2]
        sc = 300.0 / w
        pair = np.hstack([cv2.resize(before, (300, int(h * sc))),
                          cv2.resize(after, (300, int(h * sc)))])
        cv2.putText(pair, f"{t:.0f}s before", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(pair, "after", (306, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        tiles.append(pair)
    if not tiles:
        return None
    rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
    if len(rows) > 1 and rows[-1].shape[1] != rows[0].shape[1]:
        pad = rows[0].shape[1] - rows[-1].shape[1]
        rows[-1] = np.hstack([rows[-1], np.zeros((rows[-1].shape[0], pad, 3), np.uint8)])
    sheet = np.vstack(rows)
    cv2.imwrite(str(path), sheet)
    return path


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Remove a burned-in watermark from video you own.")
    ap.add_argument("video", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--rights", choices=["own", "licensed"],
                    help="own = you made it; licensed = you hold a licence. Required to process; "
                         "recorded in the sidecar. Not needed for --probe/--selftest.")
    ap.add_argument("--mode", default="matte", choices=["matte", "soft", "delogo", "crop"])
    ap.add_argument("--calibrate",
                    help="matte mode: t:x,y,w,h where the mark sits on a plain background, "
                         "or 'auto' to probe for it")
    ap.add_argument("--probe", type=int, nargs="?", const=12, default=0, metavar="N",
                    help="scan N frames, report candidate marks and a verified --calibrate, then exit")
    ap.add_argument("--selftest", action="store_true",
                    help="verify the engine on a synthetic clip and exit")
    ap.add_argument("--min-score", type=float, default=0.35)
    ap.add_argument("--min-ratio", type=float, default=1.35)
    ap.add_argument("--soft-on-miss", action="store_true", default=True,
                    help="matte mode: run soft suppression on frames where the mark is not found")
    ap.add_argument("--no-soft-on-miss", dest="soft_on_miss", action="store_false")
    ap.add_argument("--check", action="store_true", default=True,
                    help="matte mode: keep whichever candidate leaves the least mark residue")
    ap.add_argument("--no-check", dest="check", action="store_false")
    ap.add_argument("--window", type=int, default=41, help="soft mode: background window (px)")
    ap.add_argument("--threshold", type=float, default=24.0, help="soft mode: fade bumps below this")
    ap.add_argument("--falloff", type=float, default=60.0, help="soft mode: keep bumps above this")
    ap.add_argument("--passes", type=int, default=1)
    ap.add_argument("--box", action="append", default=[], help="delogo: x,y,w,h (repeatable)")
    ap.add_argument("--crop", type=int, default=0, help="crop mode: pixels to cut from the bottom")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preview", type=int, default=6, help="before/after samples (0=off)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.video:
        ap.error("a video file is required (or use --selftest)")

    src = Path(a.video)
    out = Path(a.out) if a.out else None
    if not src.exists():
        sys.exit(f"no such file: {src}")
    if out is not None and out.exists() and not a.force:
        sys.exit(f"{out} exists; pass --force to overwrite")

    info = video_info(src)
    if a.probe:
        sheet = out.with_name(out.stem + "_probe.png") if out else Path("dewatermark_probe.png")
        probe(src, info, a.probe, sheet)
        sys.exit(0)
    if out is None:
        ap.error("--out is required to write a result")
    if not a.rights:
        ap.error("--rights own|licensed is required: only process footage you made or licensed")

    out.parent.mkdir(parents=True, exist_ok=True)
    tpl = cal = None
    if a.mode == "matte":
        if not a.calibrate or a.calibrate == "auto":
            a.calibrate = auto_calibrate(src, info)
        try:
            cal = calibrate(src, a.calibrate)
        except ValueError as e:
            sys.exit(f"--calibrate {a.calibrate} rejected: {e}. Run --probe to find a usable box.")
        tpl = make_template(cal)
        print(f"calibrated: alpha={cal['alpha']:.3f} white={cal['white']:.0f} "
              f"residual={cal['resid']:.1f} mark={cal['matte'].shape[1]}x{cal['matte'].shape[0]}px")

    # ---- delogo / crop: single ffmpeg pass
    if a.mode in ("delogo", "crop"):
        if a.mode == "delogo":
            if not a.box:
                sys.exit("delogo needs --box x,y,w,h")
            vf = ",".join(f"delogo=x={b.split(',')[0]}:y={b.split(',')[1]}:"
                          f"w={b.split(',')[2]}:h={b.split(',')[3]}"
                          for b in a.box)
        else:
            if a.crop <= 0:
                sys.exit("crop needs --crop <pixels>")
            keep = info["h"] - a.crop
            vf = f"crop={info['w']}:{keep}:0:0,scale={info['w']}:{info['h']}:flags=lanczos"
        cmd = [tool("ffmpeg"), "-v", "error", "-y", "-i", str(src), "-vf", vf,
               "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
               "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)]
        subprocess.run(cmd, check=True)
        hits = None
    else:
        state = {"found": 0, "missed": 0}

        def frames():
            for fr in iter_frames(src, info):
                if a.mode == "soft":
                    o = fr
                    for _ in range(max(1, a.passes)):
                        o = suppress_soft(o, a.window, a.threshold, a.falloff)
                    yield o
                    continue
                soft = fr
                for _ in range(max(1, a.passes)):
                    soft = suppress_soft(soft, a.window, a.threshold, a.falloff)
                box, _ = detect(gray(fr), tpl, cal, a.min_score, a.min_ratio)
                if box is None:
                    state["missed"] += 1
                    yield soft if a.soft_on_miss else fr
                    continue
                state["found"] += 1
                cands = [fr, soft, unblend(soft, box, cal)]
                if a.check:
                    scored = [(mark_energy(c, box, cal["matte"]), i) for i, c in enumerate(cands)]
                    scored = [s for s in scored if s[0] is not None]
                    if scored:
                        scored.sort()
                        yield cands[scored[0][1]]
                        continue
                yield cands[2]

        encode(frames(), info, src, out, a.crf)
        hits = state if a.mode == "matte" else None

    # ---- sidecar + preview
    side = {
        "source": str(src.resolve()), "output": str(out.resolve()),
        "rights": a.rights, "mode": a.mode,
        "params": {k: v for k, v in vars(a).items()
                   if k not in ("video", "out", "force", "selftest")},
        "size": os.path.getsize(out),
        "note": "Watermark removal recorded for provenance. The human still approves the post.",
    }
    if cal:
        side["calibration"] = {"alpha": round(cal["alpha"], 4),
                               "white": round(cal["white"], 1),
                               "residual": round(cal["resid"], 2)}
    if hits:
        side["detection"] = hits
    save_json(out.with_suffix(".json"), side)

    sheet = None
    if a.preview:
        dur = info["dur"]
        times = [dur * (i + 0.5) / a.preview for i in range(a.preview)]
        sheet = preview(src, out, info, cal, times, out.with_name(out.stem + "_preview.png"))

    print(f"wrote {out}  ({info['w']}x{info['h']}, {info['dur']:.1f}s, {side['size']/1e6:.1f} MB)")
    if hits:
        total = hits["found"] + hits["missed"]
        print(f"mark located in {hits['found']}/{total} frames ({100*hits['found']/max(total,1):.0f}%)")
    if sheet:
        print(f"preview: {sheet}  <- look at it before trusting the result")
    print("Nothing was posted. Show the preview to the human and wait for a yes.")


if __name__ == "__main__":
    main()
