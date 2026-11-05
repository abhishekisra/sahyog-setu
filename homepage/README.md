# Homepage (React build) — live files

`https://sahyogsetu.in/` is a compiled React app served from `/var/www/html`
(not from Django). Its source isn't on the server, so several features were
added by hand-editing the build output. `live/` holds the files exactly as
they are live; `sync.sh` compares, pulls or deploys them.

```
homepage/sync.sh check    # does live match the repo?
homepage/sync.sh pull     # after editing live files: copy them here, then commit
homepage/sync.sh deploy   # put the repo version live (backs up first)
```

## What was added to `index.html` (all outside `#root`)
- New site header (2026-11-05). The master copy is Django's
  `custom_admin/templates/custom_admin/_ssh_header*.html`; the homepage copy is
  in `snippets/ssh-header.html` plus the same CSS in `<head>`. Change both.
  The React theme header (`header.main_header_arae`) is hidden by CSS.
- Quiz banner (2026-11-05, `snippets/quiz-banner.html`): replaces the React
  quiz section (the `section` holding `quiz_logo.png`), re-checked every 800 ms.
- Search panel, FAQ chatbot, eligibility FAB/overlay, Login/Register links,
  mobile bottom nav, count badges, route fixes, Google Translate banner fixes.
- `static/js/main.8fca9b23.p1.js` is a patched copy of the bundle (image URL
  guards) and `index.html` loads it instead of `main.8fca9b23.js`.

## If the React app is ever rebuilt
A new build gets a new `index.html` and new hashed bundle names. Don't deploy
this folder over it blindly: re-apply the blocks above to the new
`index.html` (they're plain, self-contained `<style>`/`<script>`/HTML blocks
outside `#root`), then `sync.sh pull` and update `FILES` in `sync.sh` for the
new bundle names.

Big images in `/var/www/html/assets` aren't tracked here; they don't change.
