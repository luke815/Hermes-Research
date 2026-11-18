#!/bin/sh
# Install the diligence skill where Hermes reads skills, then lock it so the
# agent's self-improvement pass cannot rewrite it. Refuses an unpinned edit and
# fails loudly when the lock cannot be taken. Re-run after any committed change
# to SKILL.md (which also needs skills/diligence/SHA256 updated).
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
: "${HOME:?HOME must be set (cron: add HOME=/home/<user> to the crontab)}"
if command -v shasum >/dev/null 2>&1; then
  actual="$(shasum -a 256 "$HERE/SKILL.md" | cut -d' ' -f1)"
else
  actual="$(sha256sum "$HERE/SKILL.md" | cut -d' ' -f1)"
fi
pinned="$(cut -d' ' -f1 "$HERE/SHA256")"
if [ "$actual" != "$pinned" ]; then
  echo "SKILL.md does not match skills/diligence/SHA256; refusing to install an unpinned edit" >&2
  exit 1
fi
DEST="${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}/research/diligence"
mkdir -p "$DEST"
cp "$HERE/SKILL.md" "$DEST/SKILL.md"
echo "installed $DEST/SKILL.md ($actual)"
if command -v hermes >/dev/null 2>&1; then
  if hermes curator lock diligence; then
    echo "locked: hermes curator lock diligence"
  else
    echo "lock failed; run: hermes curator lock diligence" >&2
    exit 1
  fi
else
  echo "hermes CLI not on PATH; run: hermes curator lock diligence" >&2
  exit 1
fi
