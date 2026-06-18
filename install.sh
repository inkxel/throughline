#!/usr/bin/env bash
#
# install.sh — fetch the Throughline scaffolder and run init.sh against a repo.
#
# Usage (local clone):
#   bash install.sh [repo-path]
#
# Usage (one-liner, from the README):
#   curl -fsSL https://raw.githubusercontent.com/inkxel/throughline/main/install.sh | bash -s -- [repo-path]
#
# [repo-path] defaults to the current directory. The scaffold is idempotent and
# merge-aware — safe to re-run; it won't clobber an existing knowledge/ or overwrite
# an existing .claude/settings.json (it merges the commit hook in).
#
# Prereqs: bash + jq (jq drives the .claude/settings.json hook merge).
# See docs/skill-notes.md → PREREQUISITES for the full dependency matrix.

set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/inkxel/throughline/main"
TARGET="${1:-$PWD}"

# ---------- install bin/throughline onto PATH ----------
_install_cli() {
  local bin_src="$1"
  local dest_dir="$HOME/.local/bin"
  mkdir -p "$dest_dir"
  ln -sf "$bin_src" "$dest_dir/throughline"
  chmod +x "$dest_dir/throughline"
  echo "✓ throughline CLI → $dest_dir/throughline"
  # Warn if the dir isn't on PATH
  case ":${PATH}:" in
    *":$dest_dir:"*) ;;
    *) echo "  ⚠  $dest_dir is not on your PATH. Add this to your shell profile:" ;;
  esac
  case ":${PATH}:" in
    *":$dest_dir:"*) ;;
    *) printf '     export PATH="%s:$PATH"\n' "$dest_dir" ;;
  esac
}

# If init.sh sits next to this script (local clone), run it directly.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/scripts/init.sh" ]; then
  echo "→ Running local scaffolder against: $TARGET"
  _install_cli "$SCRIPT_DIR/bin/throughline"
  exec bash "$SCRIPT_DIR/scripts/init.sh" "$TARGET"
fi

# Otherwise (piped from curl), fetch init.sh + bin/throughline into a temp dir.
command -v jq >/dev/null 2>&1 || { echo "error: jq is required (used for the settings.json hook merge). Install it and retry." >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "→ Fetching scaffolder…"
curl -fsSL "$REPO_RAW/scripts/init.sh" -o "$TMP/init.sh"
mkdir -p "$TMP/bin"
curl -fsSL "$REPO_RAW/bin/throughline" -o "$TMP/bin/throughline"
chmod +x "$TMP/bin/throughline"

# For curl installs, copy (not symlink) to ~/.local/bin so it survives TMP cleanup.
dest_dir="$HOME/.local/bin"
mkdir -p "$dest_dir"
cp "$TMP/bin/throughline" "$dest_dir/throughline"
chmod +x "$dest_dir/throughline"
echo "✓ throughline CLI → $dest_dir/throughline"
case ":${PATH}:" in
  *":$dest_dir:"*) ;;
  *) printf '  ⚠  %s is not on your PATH. Add:\n     export PATH="%s:$PATH"\n' "$dest_dir" "$dest_dir" ;;
esac

echo "→ Running scaffolder against: $TARGET"
bash "$TMP/init.sh" "$TARGET"
