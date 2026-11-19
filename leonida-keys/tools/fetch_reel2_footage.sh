#!/usr/bin/env bash
# Re-fetch the official-trailer footage clips used by Reel 2 (launch news).
# Source: tafsirulislamapon/Gta6GASP (a GTA VI website recreation that vendors
# short official trailer/postcard clips as regular git blobs). Fetched through
# the GitHub blobs API, which is reachable from this sandbox.
# NOTE: these are Rockstar's copyrighted trailer clips — used here only as
# transformed fair-use commentary material. Never re-upload them raw.
set -euo pipefail
cd "$(dirname "$0")/../.."   # leonida-keys/
mkdir -p media/raw
cd media/raw
B="https://api.github.com/repos/tafsirulislamapon/Gta6GASP/git/blobs"
curl -s -H "Accept: application/vnd.github.raw" "$B/a23ac7740161f8c569ac6d600f91661ab9767421" -o gasp_out1.mp4
curl -s -H "Accept: application/vnd.github.raw" "$B/18506a758f40eff35993d1f2c799f8431aff454b" -o gasp_out2.mp4
curl -s -H "Accept: application/vnd.github.raw" "$B/5fb435c06a49dc170b1acb0ddc13b9e613882535" -o gasp_out3.mp4
curl -s -H "Accept: application/vnd.github.raw" "$B/6f8741238d73e402068e4b26f41d5496738bf8e7" -o gasp_postcard.mp4
echo "footage re-fetched:"; ls -la gasp_*.mp4
