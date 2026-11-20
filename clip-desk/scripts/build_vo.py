#!/usr/bin/env python3
"""Assemble a conformed voiceover track from per-block TTS files.

Blocks are consecutive groups of script lines, one audio file each (the TTS tool
reads a whole paragraph better than a lone sentence). Each block is split on
silence and its segments are matched to the block's lines by minimising the
distance to character-proportional targets, so no word gets cut in half. Each
line is then fitted into its slot (atempo, capped), placed at its start, and the
following lines are pushed instead of overlapping. Writes the VO and rewrites the
script with conformed `t0`/`t1` (`*_vo.json`) so captions follow the dub.

usage:
  build_vo.py --script script.json --vo-dir vo --out vo.wav \
      --blocks blockA:0:5,blockB:5:10,blockC:10:15,blockD:15:21,tail1:21:22
"""
import argparse, json, os, subprocess, sys, wave
from itertools import combinations
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import tool  # noqa: E402

FF = tool("ffmpeg")
SR = 48000

def _parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--vo-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--blocks", required=True,
                    help="name:from:to,name:from:to,... (0-based line ranges)")
    return ap.parse_args()


args = _parse()
blocks = []
for spec in args.blocks.split(","):
    name, a, b = spec.split(":")
    blocks.append((name, int(a), int(b)))

def decode(p):
    out = subprocess.run([FF,"-v","error","-i",str(p),"-ac","1","-ar",str(SR),"-f","f32le","-"],
                         capture_output=True).stdout
    return np.frombuffer(out, np.float32)

def split_silence(x, hop=0.02):
    n=int(hop*SR); frames=len(x)//n
    e=np.array([np.sqrt((x[i*n:(i+1)*n]**2).mean()) for i in range(frames)])
    thr=max(e.max()*0.05, np.percentile(e,8)*1.6, 1e-4)
    v=e>thr; segs=[]; i=0
    while i<frames:
        if v[i]:
            j=i
            while j<frames and (v[j] or (j+2<frames and v[j+1]) or (j+3<frames and v[j+2])): j+=1
            if j-i>=int(0.05/hop): segs.append([i*hop, j*hop])
            i=j
        else: i+=1
    merged=[]
    for s in segs:
        if merged and s[0]-merged[-1][1] < 0.28: merged[-1][1]=s[1]   # keep real pauses split
        else: merged.append(s)
    return merged

def partition(segs, want, weights):
    """Group consecutive segments into `want` lines, boundaries nearest the char-proportional targets."""
    m=len(segs); total=segs[-1][1]
    tgt=np.cumsum(weights)[:-1]*total
    best=None
    for cuts in combinations(range(1,m), want-1) if want>1 else [()]:
        if len(cuts)!=want-1: continue
        bounds=[0]+list(cuts)+[m]
        cost=0.0
        for gi in range(want-1):
            edge=segs[bounds[gi+1]-1][1]
            cost+=abs(edge-tgt[gi])
        if best is None or cost<best[0]: best=(cost,cuts)
    if best is None: return [[0,m]]
    bounds=[0]+list(best[1])+[m]
    return [ [segs[bounds[g]][0], segs[bounds[g+1]-1][1]] for g in range(want) ]

def atempo(x, factor):
    if abs(factor-1.0) < 0.01: return x
    open("/tmp/_a.raw","wb").write(x.astype(np.float32).tobytes())
    out=subprocess.run([FF,"-y","-v","error","-f","f32le","-ar",str(SR),"-ac","1","-i","/tmp/_a.raw",
                        "-filter:a",f"atempo={factor:.3f}","-f","f32le","-"],capture_output=True).stdout
    return np.frombuffer(out,np.float32)

lines=json.load(open(args.script,encoding="utf-8"))
for l in lines: l.pop("t0_orig", None)
pieces={}
for name,a,b in blocks:
    x=decode(os.path.join(args.vo_dir, name + ".mp3"))
    if len(x) == 0:
        sys.exit(f"empty decode: {os.path.join(args.vo_dir, name)}.mp3")
    segs=split_silence(x)
    weights=[len(lines[i]['ar']) for i in range(a,b)]
    parts=partition(segs, b-a, [w/sum(weights) for w in weights])
    print(f"{name}: {len(segs)} silence segments -> {len(parts)} lines")
    for k,(s0,s1) in enumerate(parts):
        pieces[a+k]=(x[int(s0*SR):int(s1*SR)], s1-s0)

buf=np.zeros((int((max(l['t1'] for l in lines)+1.0)*SR),2),np.float32); problems=[]; cursor=0.0
for i,(seg,dur) in sorted(pieces.items()):
    ln=lines[i]
    nxt=lines[i+1]['t0'] if i+1 < len(lines) else ln['t1']+0.6
    avail=max(ln['t1'],nxt)-ln['t0']
    f=dur/avail
    if f>1.02:
        at=min(f,1.2); seg=atempo(seg,at)
        if f>1.25: problems.append((i+1,round(dur,2),round(avail,2)))
    start=max(ln['t0'], cursor)          # conform: never overlap the previous line
    ln['t0_orig']=ln['t0']; ln['t0']=round(start,3)
    dur=len(seg)/SR
    ln['t1']=round(max(start+dur, min(ln['t1'], start+dur+0.25)),3)
    cursor=start+dur+0.10
    k=int(0.012*SR)
    if len(seg)>2*k:
        seg=seg.copy(); seg[:k]*=np.linspace(0,1,k); seg[-k:]*=np.linspace(1,0,k)
    st=int(ln['t0']*SR); en=min(len(buf),st+len(seg))
    buf[st:en,0]+=seg[:en-st]; buf[st:en,1]+=seg[:en-st]
    print(f"  line {i+1:2d} {ln['t0']:5.1f}s  speech {dur:4.2f}s  slot {avail:4.2f}s  {'ok' if f<=1.02 else 'x%.2f'%min(f,1.2)}")
print("overruns beyond 1.2x:", problems)
buf=buf/max(1.0,float(np.abs(buf).max())/0.95)
with wave.open(args.out,"wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf*32767).astype(np.int16).tobytes())
print("wrote", args.out, f"{len(buf)/SR:.1f}s")
conformed = os.path.splitext(args.out)[0] + "_script.json"
json.dump(lines, open(conformed, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
shift = max((abs(l['t0'] - l['t0_orig']) for l in lines if 't0_orig' in l), default=0.0)
print(f"max conform shift: {shift:.2f}s -> {conformed}")
