#!/usr/bin/env bash
# Install VSR (video-subtitle-remover) for `remove_captions.py`.
#
# VSR is ~1.7 GB of checkout plus torch, and it is NOT a dependency of this
# repo. This script always installs it OUTSIDE the repo (default ~/vsr) and
# leaves this tree untouched.
#
# usage:
#   setup_vsr.sh                    # install to ~/vsr, CPU wheels
#   setup_vsr.sh ~/vsr-cuda --cuda  # CUDA wheels
#   setup_vsr.sh --verify ~/vsr     # smoke-test an existing install, no changes
#
# After it finishes: remove_captions.py <clip> --rights own --vsr-home <dir>
set -euo pipefail

SHIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/vsr_shim"
UPSTREAM="https://github.com/YaoFANGUK/video-subtitle-remover"

if [ "${1:-}" = "--verify" ]; then
  TARGET="${2:?usage: setup_vsr.sh --verify <dir>}"
else
  TARGET="${1:-$HOME/vsr}"
  ACCEL="${2:-}"
fi

smoke() {
  local home="$1" py="$2"
  echo "== smoke test =="
  ( cd "$home" && PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
      PYTHONPATH="$SHIM${PYTHONPATH:+:$PYTHONPATH}" "$py" - <<'EOF'
import sys
sys.path.insert(0, ".")
from backend.config import config
from backend.main import SubtitleRemover  # noqa: F401
import cv2, torch, paddle
print(f"ok  paddle {paddle.__version__}  torch {torch.__version__}  cv2 {cv2.__version__}")
print(f"    cuda available: {torch.cuda.is_available()}")
EOF
  )
}

if [ "${1:-}" = "--verify" ]; then
  [ -d "$TARGET/backend" ] || { echo "not a VSR checkout: $TARGET" >&2; exit 1; }
  PY="$TARGET/.venv/bin/python"
  [ -x "$PY" ] || PY="${VSR_PYTHON:-python3}"
  smoke "$TARGET" "$PY"
  exit 0
fi

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
PYBIN="${PYBIN:-python3}"
"$PYBIN" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
  || { echo "need Python 3.11+ (3.12+ avoids the source patch below)" >&2; exit 1; }

if [ ! -d "$TARGET/backend" ]; then
  echo "== clone $UPSTREAM -> $TARGET (~1.7 GB, one time) =="
  git clone --depth 1 "$UPSTREAM" "$TARGET"
fi

echo "== venv =="
[ -x "$TARGET/.venv/bin/python" ] || "$PYBIN" -m venv "$TARGET/.venv"
PIP="$TARGET/.venv/bin/pip"
PY="$TARGET/.venv/bin/python"
"$PIP" install -q --upgrade pip wheel

echo "== torch =="
if [ "$ACCEL" = "--cuda" ]; then
  "$PIP" install torch torchvision
else
  # CPU box: the default wheels drag in ~3 GB of CUDA libraries for nothing
  "$PIP" install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

echo "== VSR runtime deps =="
"$PIP" install opencv-python-headless numpy av einops tqdm scikit-image \
  filesplit requests darkdetect pillow scipy matplotlib

echo "== OCR (pin paddle 3.0.0: 3.3.x dies on CPU) =="
"$PIP" install "paddlepaddle==3.0.0" paddleocr

echo "== patch VSR source for Python < 3.12 (PEP 701 f-string) =="
"$PY" - "$TARGET" <<'EOF'
import pathlib, sys
root = pathlib.Path(sys.argv[1])
bad = []
for p in (root / "backend").rglob("*.py"):
    try:
        compile(p.read_text(encoding="utf-8"), str(p), "exec")
    except SyntaxError as e:
        bad.append((p, e))
for p, e in bad:
    txt = p.read_text(encoding="utf-8")
    fixed = txt.replace("{frame_info['len']}", '{frame_info["len"]}')
    if fixed != txt:
        p.write_text(fixed, encoding="utf-8")
        print(f"  patched {p.relative_to(root)}:{e.lineno}")
    else:
        print(f"  !! cannot patch {p.relative_to(root)}:{e.lineno}: {e.msg}")
        sys.exit(1)
if not bad:
    print("  nothing to patch")
EOF

smoke "$TARGET" "$PY"

cat <<EOF

done. install: $TARGET
next:
  python3 clip-desk/scripts/remove_captions.py <clip> --rights own \\
      --vsr-home "$TARGET" --inpaint-mode lama
EOF
