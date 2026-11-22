#!/usr/bin/env python3
"""Scaffold the next Quran verse-card video and print the exact command block.

Does three things, all offline and idempotent:
  1. works out the next free slot number from outputs/ (and refuses to reuse one),
  2. creates assets/quran/<slot>/, jobs/<slot>/, metadata/<slot>/,
  3. prints (or writes, with --write) the command block for this specific video,
     with the duration, verse range and paths already filled in.

Nothing is downloaded, rendered or posted. It only removes typing.

Examples:
  python tools/new_video.py --surah al-baqarah --ayah 2:152-153 \
      --reciter "Yasser ad-Dussary" --dry-run

  python tools/new_video.py --surah al-baqarah --ayah 2:152-153 \
      --reciter "Yasser ad-Dussary" --duration 26.2 --write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
ASSETS = REPO / "assets" / "quran"
JOBS = REPO / "jobs"
META = REPO / "metadata"

SLOT_RE = re.compile(r"^(\d{3})_")
# keys are lowercase with words separated by single spaces (see normalise_key)
RECITER_ALIASES = {
    "yasser ad dussary": ("yasser-ad-dussary", "Yasser ad-Dussary", 97),
    "yasser addussary": ("yasser-ad-dussary", "Yasser ad-Dussary", 97),
    "yasser al dossari": ("yasser-ad-dussary", "Yasser ad-Dussary", 97),
    "yasser aldossari": ("yasser-ad-dussary", "Yasser ad-Dussary", 97),
    "mishari al afasy": ("afasy", "Mishari Rashid al-ʿAfasy", 7),
    "mishary alafasy": ("afasy", "Mishari Rashid al-ʿAfasy", 7),
    "mishari rashid al afasy": ("afasy", "Mishari Rashid al-ʿAfasy", 7),
    "abdul basit": ("abdul-basit", "Abdul Basit (Murattal)", 2),
    "abdul basit murattal": ("abdul-basit", "Abdul Basit (Murattal)", 2),
}


def slugify(value: str) -> str:
    v = value.lower()
    v = v.replace("ʿ", "").replace("'", "").replace("’", "").replace("`", "")
    v = re.sub(r"[^a-z0-9]+", "-", v)
    return v.strip("-")


def used_slots() -> set[int]:
    slots: set[int] = set()
    for base in (OUTPUTS, ASSETS, META):
        if not base.exists():
            continue
        for child in base.iterdir():
            m = SLOT_RE.match(child.name)
            if m:
                slots.add(int(m.group(1)))
    return slots


def next_slot() -> int:
    used = used_slots()
    n = 0
    while n in used:
        n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scaffold the next Quran video slot and print its build commands.")
    ap.add_argument("--surah", required=True, help='surah name, e.g. "al-baqarah" or "maryam"')
    ap.add_argument("--ayah", required=True, help="ayah range, e.g. 2:152-153 or 19:30-33")
    ap.add_argument("--reciter", required=True, help='reciter name, e.g. "Yasser ad-Dussary"')
    ap.add_argument("--surah-title", help='header text, default "Surah <Title>"')
    ap.add_argument("--duration", type=float, default=26.2,
                    help="final video duration in seconds (recitation span + 1.2 s)")
    ap.add_argument("--clip-seconds", type=float, default=None,
                    help="length of the chosen background clip, used to compute the setpts factor")
    ap.add_argument("--slot", type=int, default=None, help="override the auto slot number")
    ap.add_argument("--dry-run", action="store_true", help="print only, create nothing")
    ap.add_argument("--write", action="store_true", help="also write the command block to the job folder")
    args = ap.parse_args(argv)

    surah_slug = slugify(args.surah).replace("-", "_")
    ayah = args.ayah.strip()
    m = re.match(r"^(\d{1,3}):(\d{1,3})-(?:(\d{1,3}):)?(\d{1,3})$", ayah)
    if not m:
        print("ERROR: --ayah must look like 2:152-153 or 19:30-33", file=sys.stderr)
        return 2
    surah_no, first_ayah, _mid_surah, last_ayah = m.groups()
    ayah = "%s:%s-%s" % (surah_no, first_ayah, last_ayah)

    rec_key = re.sub(r"[^a-z0-9]+", " ", args.reciter.replace("ʿ", "").lower()).strip()
    slug_part, rec_name, rec_id = RECITER_ALIASES.get(
        rec_key, (slugify(args.reciter), args.reciter, None)
    )
    if rec_id is None:
        print(
            "WARN: unknown reciter %r — check its QF chapter-reciter id in\n"
            "      https://api.quran.com/api/v4/resources/chapter_reciters before rendering"
            % args.reciter,
            file=sys.stderr,
        )

    slot = args.slot if args.slot is not None else next_slot()
    if slot in used_slots():
        print("ERROR: slot %03d is already used — slots are permanent" % slot, file=sys.stderr)
        return 2

    nn = "%03d" % slot
    ayah_token = "%s_%s" % (surah_no, first_ayah)
    if last_ayah != first_ayah:
        ayah_token += "-%s" % last_ayah
    name = "%s_%s_%s" % (nn, surah_slug, ayah_token)
    name = "%s_%s" % (name, slug_part)
    out_file = "outputs/quran-%s_en_1080x1920_v1.mp4" % name
    title = args.surah_title or (
        "Surah " + "-".join(part.capitalize() for part in args.surah.split("-"))
    )

    verse_count = int(last_ayah) - int(first_ayah) + 1

    lines: list[str] = []
    add = lines.append
    add("#!/usr/bin/env bash")
    add("# Video %s — %s %s — %s" % (nn, title, ayah, rec_name))
    add("# Generated by tools/new_video.py. Read docs/RECIPE.md before running.")
    add("set -euo pipefail")
    add("cd \"$(dirname \"$0\")/..\"")
    add("")
    add("J=jobs/%s" % name)
    add("A=assets/quran/%s" % name)
    add("M=metadata/%s" % name)
    add("OUT=%s" % out_file)
    add("PY=.venv/bin/python")
    add("FF=.venv/bin/ffmpeg")
    add("")
    add("# 0) sanitise the input: print QR/pin frames to be sure the clip is clean")
    add("#    (check for burned logos, captions or app UI before continuing)")
    add("")
    add("# 1) audio polish — hall space + clarity, words and timing untouched")
    add("\"$PY\" clip-desk/scripts/quran_audio_polish.py \\")
    add("  --in \"$A/recitation.m4a\" --out \"$J/recitation_polished.m4a\" \\")
    add("  --wet 0.15 --predelay 45 --target-lufs -14.5 --ceiling -1.5 --tail 0.4")
    add("")
    add("# 2) single-clip background (never reuse a clip listed in docs/ASSET-REGISTRY.md)")
    if args.clip_seconds:
        factor = round(args.duration / args.clip_seconds, 4)
        add("#    source clip is %.3f s -> setpts factor %.4f for %.1f s" % (args.clip_seconds, factor, args.duration))
        add("CLIP=\"$A/pinterest/<chosen-clip>.mp4\"")
        add("\"$FF\" -y -i \"$CLIP\" \\")
        add("  -vf \"setpts=%s*PTS,fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920\" \\" % factor)
        add("  -an -t %.1f -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart \\" % args.duration)
        add("  \"$A/background.mp4\"")
    else:
        add("#    pass --clip-seconds <len> to have the setpts factor computed for you")
    add("")
    add("# 3) visual base: black card + rounded popup + slow push-in")
    add("\"$PY\" clip-desk/scripts/quran_visual.py \\")
    add("  --background \"$A/background.mp4\" --out \"$J/visual_base.mp4\" \\")
    add("  --duration %.3f --intro 0.8 --pop-duration 0.7 --fade-in 0.35 \\" % args.duration)
    add("  --popup-top 340 --popup-width 1000 --popup-height 780 --radius 90 \\")
    add("  --dim 0.10 --glow-strength 0.055 --border-strength 0.20 \\")
    add("  --zoom-start 1.03 --zoom-end 1.00")
    add("")
    add("# 4) captions + final MP4 (dry-run first!)")
    add("CAP_ARGS=(")
    add("  --verses \"$J/verses.json\" --timings \"$J/timings.json\" --range %s" % ayah)
    add("  --translation-overrides \"$J/translation_overrides.json\"")
    add("  --translation-edition 'english_saheeh v1.1.2 / QuranEnc.com'")
    add("  --translation-credit 'English Translation - Noor International Center'")
    add("  --reciter '%s'" % rec_name)
    if rec_id:
        add("  --timing-source 'QF chapter_recitations/%d/<surah>?segments=true'" % rec_id)
    add("  --surah-name '%s'" % title)
    add("  --out \"$J/captions.ass\" --srt \"$J/review.srt\"")
    add("  --font-dir clip-desk/skills/quran-subtitles/fonts --layers header,arabic,english,ref")
    add("  --width 1080 --height 1920 --fps 30")
    add("  --header-y 270 --arabic-y 1275 --english-y 1450 --ref-y 1605")
    add("  --arabic-size 62 --english-size 46 --header-size 36 --ref-size 28")
    add("  --arabic-cpl 36 --arabic-lines 2 --english-cpl 42")
    add("  --fade-ms 400 --dim 0 --strict")
    add("  --auto-offset --offset-ms 800 --source-start-ms 0 --audio-start-ms 0")
    add("  --video-duration %.3f --max-duration 15 --max-cps 20" % args.duration)
    add("  --source-video \"$J/visual_base.mp4\" --audio \"$J/recitation_polished.m4a\"")
    add("  --video-out \"$OUT\" --credits-out \"$M/credits.txt\"")
    add(")")
    add("")
    add("# validate the join before encoding (~2 s instead of a 2-minute render)")
    add("\"$PY\" clip-desk/scripts/quran_subtitles.py \"${CAP_ARGS[@]}\" --dry-run")
    add("\"$PY\" clip-desk/scripts/quran_subtitles.py \"${CAP_ARGS[@]}\"")
    add("")
    add("# 5) QA package")
    add("\"$FF\" -y -ss %.1f -i \"$OUT\" -frames:v 1 -update 1 \"$M/poster.png\"" % (args.duration * 0.7))
    add("\"$FF\" -y -i \"$OUT\" -vf \"select='eq(n,12)+eq(n,90)+eq(n,300)+eq(n,420)+eq(n,600)+eq(n,760)',\\")
    add("setpts=N/FRAME_RATE/TB,scale=540:960,tile=2x3:padding=8:margin=8\" -frames:v 1 -update 1 \"$M/qa.png\"")
    add("\"$FF\" -i \"$OUT\" -vf blackdetect=d=0.3:pix_th=0.01 -an -f null - 2>&1 | grep black_ || true")
    add("\"$FF\" -i \"$OUT\" -af loudnorm=print_format=summary -f null - 2>&1 | grep 'Input ' || true")
    add("")
    add("echo \"open $M/poster.png and $M/qa.png and LOOK at them before showing the human\"")
    add("echo \"then: update docs/CATALOG.md, mark the clip spent in docs/ASSET-REGISTRY.md, commit\"")

    text = "\n".join(lines) + "\n"

    print("slot      : %s" % nn)
    print("video name: %s" % name)
    print("output    : %s" % out_file)
    print("verses    : %s (%d ayat)" % (ayah, verse_count))
    print("reciter   : %s (QF id %s)" % (rec_name, rec_id if rec_id else "UNKNOWN — verify"))
    print("duration  : %.1f s" % args.duration)
    if args.dry_run:
        print("\n--- commands (dry run, nothing created) ---\n")
        print(text)
        return 0

    for base in (ASSETS / name, JOBS / name, META / name):
        base.mkdir(parents=True, exist_ok=True)
    print("\ncreated: %s/, %s/, %s/" % (ASSETS / name, JOBS / name, META / name))
    if args.write:
        target = JOBS / name / "build.sh"
        target.write_text(text, encoding="utf-8")
        target.chmod(0o755)
        print("wrote  : %s" % target)
    else:
        print("\n--- commands ---\n")
        print(text)

    # starter JSON so the next step is editing, not inventing shapes
    tpl = {
        "verses.json": {"source": "Quran Foundation by_key text_qpc_hafs", "verses": {}},
        "timings.json": {
            "reciter": rec_name,
            "source_url": "https://api.quran.com/api/v4/chapter_recitations/%s/<surah>?segments=true" % (rec_id or "<id>"),
            "audio_url": "",
            "timestamps": [],
        },
        "translation_overrides.json": {"_meta": {"translation_name": "", "source_url": ""}},
    }
    for fname, payload in tpl.items():
        path = JOBS / name / fname
        if not path.exists():
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print("template: %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
