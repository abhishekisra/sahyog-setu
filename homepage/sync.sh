#!/bin/bash
# Keeps the homepage (React build in /var/www/html, NOT part of Django) under
# version control. The live files were hand-edited after the React build
# (new site header, quiz banner, search, chatbot, eligibility FAB, login links,
# bottom nav, Google Translate, bundle patch ...), so a fresh React build would
# silently wipe all of that. This folder is the record of what is live.
#
#   homepage/sync.sh check    live vs repo; exit 1 if anything differs
#   homepage/sync.sh pull     copy live -> repo (after editing the live site), then commit
#   homepage/sync.sh deploy   back up live, then copy repo -> live (e.g. after a React rebuild wiped it)
set -euo pipefail
LIVE="${LIVE:-/var/www/html}"
REPO="$(cd "$(dirname "$0")" && pwd)/live"
FILES="index.html sw.js sitemap.xml robots.txt manifest.json favicon.ico asset-manifest.json
static/js/main.8fca9b23.js static/js/main.8fca9b23.p1.js static/js/453.0b2b2079.chunk.js
static/css/main.f71db398.css assets/img/favicon.png"

case "${1:-check}" in
  check)
    drift=0
    for f in $FILES; do
      if ! cmp -s "$LIVE/$f" "$REPO/$f"; then echo "DIFFERS: $f"; drift=1; fi
    done
    [ $drift -eq 0 ] && echo "OK: live homepage matches the repo ($(echo $FILES | wc -w) files)"
    exit $drift ;;
  pull)
    for f in $FILES; do cp -p "$LIVE/$f" "$REPO/$f"; done
    echo "Copied live -> repo. Review with 'git diff homepage/' and commit." ;;
  deploy)
    bk=/root/sahyogsetu-backups/homepage-before-deploy-$(date +%Y%m%d-%H%M%S)
    mkdir -p "$bk"
    for f in $FILES; do
      [ -f "$LIVE/$f" ] && mkdir -p "$bk/$(dirname "$f")" && cp -p "$LIVE/$f" "$bk/$f"
      mkdir -p "$LIVE/$(dirname "$f")" && cp -p "$REPO/$f" "$LIVE/$f"
    done
    echo "Deployed repo -> live. Previous live files saved in $bk" ;;
  *) echo "usage: $0 check|pull|deploy" >&2; exit 2 ;;
esac
