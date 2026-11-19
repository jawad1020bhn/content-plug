#!/usr/bin/env python3
"""Build Reel 1 (launch welcome) for Leonida Keys.

5 visual segments over 4 AI concept images, crossfaded, with Ken Burns motion,
plugin-style burned captions (ASS, same styles as cut.py), a synthesized
synthwave pulse bed, and the narrator VO segments placed exactly on the
timeline. Output: media/edits/reel1_leonida_keys.mp4 (1080x1920@30, -14 LUFS).
"""
import subprocess, sys
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent          # leonida-keys/
RAW, EDITS = PAGE / "media" / "raw", PAGE / "media" / "edits"
JOBS = PAGE / "jobs" / "reel1"
JOBS.mkdir(parents=True, exist_ok=True)
EDITS.mkdir(parents=True, exist_ok=True)
FF = str(next(d for d in (Path(sys.executable).parent, Path(sys.prefix) / "bin")
            if (d / "ffmpeg").exists()) / "ffmpeg")
FFPR = str(Path(FF).parent / "ffprobe")
W, H, FPS, XF = 1080, 1920, 30, 0.4                     # size, fps, xfade secs

IMGS = [RAW / "reel1_hero.jpg", RAW / "reel1_stilts.jpg", RAW / "reel1_boat.jpg",
        RAW / "reel1_stilts.jpg", RAW / "reel1_cta.jpg"]
VOS = [RAW / f"vo_{i}.mp3" for i in range(1, 6)]
OUT = EDITS / "reel1_leonida_keys.mp4"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(map(str, cmd))[:220]}\n{r.stderr[-1800:]}")


def dur(p):
    r = subprocess.run([FFPR, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def ts(t):
    t = max(0.0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


# ---- 1. synthwave pulse bed (bass + pad + offbeat hats, 108 BPM) ----------------
BEAT = JOBS / "beat.wav"
B = 0.5556                                              # beat length @108bpm
env = f"pow(max(0,1-mod(t,{B})/{B}),2.2)"
hat = f"pow(max(0,1-mod(t+{B/2},{B})/0.09),3)"
expr = (f"(0.30*sin(2*PI*55*t)+0.18*sin(2*PI*110*t))*{env}"
        f"+0.085*(sin(2*PI*220*t)+sin(2*PI*261.63*t)+sin(2*PI*329.63*t))*(0.55+0.45*sin(2*PI*0.22*t))"
        f"+0.045*(2*random(0)-1)*{hat}")
e = expr.replace(",", "\\,")                           # escape commas for lavfi parser
run([FF, "-y", "-v", "error", "-f", "lavfi", "-t", "25",
     "-i", f"aevalsrc={e}|{e}:s=48000", "-c:a", "pcm_s16le", str(BEAT)])

# ---- 2. timeline from measured VO durations -------------------------------------
vd = [dur(p) for p in VOS]
seg = [d + 0.62 for d in vd]                            # 0.3 lead + 0.32 tail per segment
starts, acc = [], 0.0
for k, d in enumerate(seg):
    starts.append(acc - XF * k if k else 0.0)
    acc += d
T = acc - XF * (len(seg) - 1)                           # final duration
print(f"VO durations: {[round(d,2) for d in vd]}  -> total {T:.2f}s")

# ---- 3. ASS captions (plugin styles) --------------------------------------------
HDR = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Arial Black,88,&H00FFFFFF,&H0000E5FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1
Style: Hook,Arial Black,68,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,18,0,8,70,70,170,1
Style: CTA,Arial Black,84,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,16,0,5,50,50,0,1
Style: Mark,Arial,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,-1,0,0,100,100,0,0,1,5,1,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
Y = (c := "{\\c&H0000E5FF&}") and "{\\c&H00FFFFFF&}"    # yellow highlight on/off
ev = [
    f"Dialogue: 0,{ts(0)},{ts(T)},Mark,,0,0,0,,{{\\pos(540,80)\\alpha&H30&}}@LeonidaKeysHQ",
    f"Dialogue: 1,{ts(0)},{ts(starts[0]+seg[0]-0.15)},Hook,,0,0,0,,{{\\fad(150,220)}}GTA 6 IS FINALLY LIVE",
    f"Dialogue: 0,{ts(starts[1]+0.35)},{ts(starts[1]+seg[1]-0.25)},Cap,,0,0,0,,{{\\pos(540,1380)}}The story starts in {c}LEONIDA KEYS{Y}",
    f"Dialogue: 0,{ts(starts[2]+0.35)},{ts(starts[2]+seg[2]-0.25)},Cap,,0,0,0,,{{\\pos(540,1380)}}Real islands. Long causeways. {c}BOATS{Y} are the way.",
    f"Dialogue: 0,{ts(starts[3]+0.35)},{ts(starts[3]+seg[3]-0.25)},Cap,,0,0,0,,{{\\pos(540,1380)}}{c}KEY LENTO{Y} — Jason's stilt-house home",
    f"Dialogue: 1,{ts(starts[4]+0.45)},{ts(T-0.1)},CTA,,0,0,0,,{{\\pos(540,890)\\fad(220,0)}}FOLLOW FOR EVERY KEY\\NTO LEONIDA",
    f"Dialogue: 0,{ts(starts[4]+0.6)},{ts(T-0.1)},Mark,,0,0,0,,{{\\pos(540,1160)\\fs46}}secrets · cars · news · moments",
]
ASS = JOBS / "captions.ass"
ASS.write_text(HDR + "\n".join(ev) + "\n", encoding="utf-8")

# ---- 4. render ------------------------------------------------------------------
zooms = [f"min(1.0+0.0011*on,1.15)", "1.08", f"min(1.0+0.0014*on,1.18)", "1.10", "max(1.12-0.0009*on,1.0)"]
pans = ["iw/2-(iw/zoom/2)", None, "iw/2-(iw/zoom/2)", None, "iw/2-(iw/zoom/2)"]
fc, maps = [], []
for k in range(5):
    F = int(round(seg[k] * FPS))
    if k == 1:   x = f"(iw-iw/zoom)*on/{F}"
    elif k == 3: x = f"(iw-iw/zoom)*(1-on/{F})"
    else:        x = pans[k]
    y = "ih/2-(ih/zoom/2)"
    fc.append(f"[{k}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"zoompan=z='{zooms[k]}':x='{x}':y='{y}':d={F}:s={W}x{H}:fps={FPS},"
              f"format=yuv420p,setsar=1[v{k}]")
prev = "v0"
for k in range(1, 5):
    off = starts[k]
    out = f"x{k}"
    fc.append(f"[{prev}][v{k}]xfade=transition=fade:duration={XF}:offset={off:.3f}[{out}]")
    prev = out
sub = str(ASS).replace("\\", "/").replace(":", "\\:")
fc.append(f"[{prev}]subtitles='{sub}'[vout]")

amix_in = []
for k in range(5):
    d = int((starts[k] + 0.31) * 1000)
    fc.append(f"[{5+k}:a]adelay={d}|{d}[a{k}]")
    amix_in.append(f"[a{k}]")
fc.append(f"[5:a]atrim=0:{T:.3f},volume=0.5,afade=t=in:st=0:d=0.4,"
           f"afade=t=out:st={T-1.4:.3f}:d=1.4[beat]")
fc.append("".join(amix_in) + "[beat]amix=inputs=6:duration=longest:normalize=0,"
          "loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

cmd = [FF, "-y", "-v", "error"]
for p in IMGS:
    cmd += ["-i", str(p)]
cmd += ["-i", str(BEAT)]
for p in VOS:
    cmd += ["-i", str(p)]
cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
        "-t", f"{T:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", str(OUT)]
run(cmd)
print(f"OK -> {OUT}  ({T:.2f}s, {OUT.stat().st_size/1e6:.1f} MB)")
