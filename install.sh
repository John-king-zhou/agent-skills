#!/usr/bin/env bash
# Link every skill in skills/ into the folders that coding agents read.
# Usage: ./install.sh [--force] [TARGET_DIR ...]
# Default targets: ~/.claude/skills (Claude Code) and ~/.agents/skills (other agents).
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
force=0
targets=()
for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    *) targets+=("$arg") ;;
  esac
done
[ ${#targets[@]} -gt 0 ] || targets=("$HOME/.claude/skills" "$HOME/.agents/skills")

for target in "${targets[@]}"; do
  mkdir -p "$target"
  for skill in "$repo"/skills/*/; do
    name="$(basename "$skill")"
    dest="$target/$name"
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "${skill%/}" ]; then
      continue                                  # already linked to this repo
    fi
    if [ -e "$dest" ] || [ -L "$dest" ]; then
      if [ "$force" -eq 1 ]; then
        mv "$dest" "$dest.bak.$(date +%Y%m%d%H%M%S)"
      else
        echo "skip   $dest (exists; use --force to back it up and replace)"
        continue
      fi
    fi
    ln -s "${skill%/}" "$dest"
    echo "linked $dest"
  done
done
