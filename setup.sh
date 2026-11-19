#!/usr/bin/env bash
# Recreate this workspace's environment after a fresh sandbox:
#   1. Python venv with the plugin's requirements (pypi.org is reachable)
#   2. Static ffmpeg + ffprobe binaries from npm registry tarballs
#      (registry.npmjs.org is reachable; no system ffmpeg and apt is blocked here)
# The YuNet face-detection model is committed at gtavi-claudecode/models/ so it
# does not need a download (its upstream URL redirects to a blocked host here).
# Idempotent: safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/2 Python venv =="
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r gtavi-claudecode/requirements.txt
echo "   ok: $(.venv/bin/python --version), $(( $(.venv/bin/pip list 2>/dev/null | wc -l) - 2 )) packages"

echo "== 2/2 ffmpeg / ffprobe =="
if [ ! -x .venv/bin/ffmpeg ]; then
    tmp=$(mktemp -d)
    curl -sL -o "$tmp/ffmpeg.tgz"  "https://registry.npmjs.org/@ffmpeg-installer/linux-x64/-/linux-x64-4.1.0.tgz"
    curl -sL -o "$tmp/ffprobe.tgz" "https://registry.npmjs.org/@ffprobe-installer/linux-x64/-/linux-x64-5.2.0.tgz"
    mkdir -p "$tmp/ff" "$tmp/ffpr"
    tar xzf "$tmp/ffmpeg.tgz"  -C "$tmp/ff"
    tar xzf "$tmp/ffprobe.tgz" -C "$tmp/ffpr"
    install -m 755 "$tmp/ff/package/ffmpeg"   .venv/bin/ffmpeg
    install -m 755 "$tmp/ffpr/package/ffprobe" .venv/bin/ffprobe
    rm -rf "$tmp"
fi
echo "   ok: $(.venv/bin/ffmpeg -version 2>&1 | head -1)"
echo "   ok: $(.venv/bin/ffprobe -version 2>&1 | head -1)"

echo
echo "Done. Run the plugin from the repo root (or a page folder), e.g.:"
echo "  .venv/bin/python gtavi-claudecode/scripts/trends.py --query \"gta 6\""
echo "Scripts also find .venv/bin/ffmpeg by themselves (common.py tool() fallback)."
