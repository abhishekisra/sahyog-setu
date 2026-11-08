"""2026-11-08 (user: "myScheme monthly update"): find what changed on
myscheme.gov.in for schemes we imported from there (myscheme_slug set).

Nothing in the database is changed here. Each difference becomes a
SUGGESTION in a private file; an admin approves or ignores it at
/admin/manage-schemes/myscheme-updates (schemes/myscheme_update_views.py).
Admins may have improved imported text by hand, which is why nothing is
applied automatically.

Compared fields (built exactly like import_myscheme_schemes builds them):
title, description, eligibility, required_documents, mode_of_application,
web_links. A slug that myScheme no longer returns is flagged "gone".

Runs monthly (cron); ~2 API calls per scheme with a delay, ~40 min for 4,485.
Usage: manage.py check_myscheme_updates [--limit N] [--slug SLUG ...]
"""
import html
import json
import os
import re
import time
import urllib.error

from django.core.management.base import BaseCommand

from schemes.models import Schemes
from schemes.management.commands import import_myscheme_schemes as imp

STATE_DIR = os.environ.get('SAHYOG_MYSCHEME_DIR', '/var/lib/sahyogsetu/myscheme_updates')
FIELDS = ('title', 'description', 'eligibility', 'required_documents', 'mode_of_application', 'web_links')


def _norm(h):
    t = html.unescape(re.sub(r'<[^>]+>', ' ', str(h or '')))
    return re.sub(r'\s+', ' ', t).strip().lower()


def _hash(h):
    import hashlib
    return hashlib.sha1(_norm(h).encode('utf-8')).hexdigest()[:16]


def build_fields(slug):
    """Same mapping as import_myscheme_schemes (create branch)."""
    time.sleep(imp.REQUEST_DELAY)
    detail = imp.fetch_detail(slug)["data"]
    en = detail["en"]
    basic = en["basicDetails"]; content = en["schemeContent"]
    elig_block = en.get("eligibilityCriteria", {}) or {}
    app_process = en.get("applicationProcess", []) or []
    time.sleep(imp.REQUEST_DELAY)
    try:
        docs = imp.fetch_documents(detail["_id"])["data"]["en"].get("documents_required", [])
    except Exception:
        docs = []
    description = imp.render_nodes(content.get("detailedDescription") or [])
    if not description.strip():
        brief = content.get("briefDescription", "")
        description = f"<p>{brief}</p>" if brief else ""
    eligibility = imp.render_nodes(elig_block.get("eligibilityDescription") or [])
    if not eligibility.strip():
        md = elig_block.get("eligibilityDescription_md", "")
        eligibility = f"<p>{md}</p>" if md else "<p>Refer to the official scheme page for eligibility details.</p>"
    documents = imp.render_nodes(docs) or "<p>Refer to the official scheme page for the documents list.</p>"
    mode = "".join(f"<h4>{m.get('mode', '')} Apply:</h4>{imp.render_nodes(m.get('process') or [])}" for m in app_process) \
        or "<p>Refer to the official scheme page for how to apply.</p>"
    refs = [f'<p><a href="{r["url"]}" target="_blank">{r.get("title") or "Reference"}</a></p>'
            for r in (content.get("references") or []) if r.get("url")]
    links = "".join(refs) or (f'<p><a href="https://www.myscheme.gov.in/schemes/{slug}" target="_blank">'
                               f'View Official Scheme Details (Government of India)</a></p>')
    return {'title': basic.get('schemeName') or '', 'description': description, 'eligibility': eligibility,
            'required_documents': documents, 'mode_of_application': mode, 'web_links': links}


class Command(BaseCommand):
    help = "Compare imported schemes with myscheme.gov.in and store differences as suggestions (no DB change)."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None)
        parser.add_argument('--slug', nargs='*', default=None)

    def handle(self, *args, **o):
        os.makedirs(STATE_DIR, exist_ok=True)
        qs = Schemes.objects.exclude(myscheme_slug__isnull=True).exclude(myscheme_slug='').order_by('id')
        if o['slug']:
            qs = qs.filter(myscheme_slug__in=o['slug'])
        if o['limit']:
            qs = qs[:o['limit']]
        pending, gone, same, errors, started = [], [], 0, 0, time.time()
        try:
            with open(os.path.join(STATE_DIR, 'ignored.json'), encoding='utf-8') as f:
                ignored = json.load(f)
        except (FileNotFoundError, ValueError):
            ignored = {}
        for s in qs.iterator():
            try:
                new = build_fields(s.myscheme_slug)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    gone.append({'id': s.id, 'slug': s.myscheme_slug, 'title': s.title, 'status': s.status})
                else:
                    errors += 1
                continue
            except Exception:
                errors += 1
                continue
            ign = ignored.get(str(s.id), {})
            changed = {f: new[f] for f in FIELDS if new.get(f) and _norm(new[f]) != _norm(getattr(s, f, ''))
                       and ign.get(f) != _hash(new[f])}       # an admin already said "ignore" to exactly this text
            if changed:
                pending.append({'id': s.id, 'slug': s.myscheme_slug, 'title': s.title, 'status': s.status,
                                'changed': changed, 'old': {f: getattr(s, f, '') for f in changed}})
            else:
                same += 1
        out = {'checked_at': int(time.time()), 'seconds': int(time.time() - started), 'same': same,
               'errors': errors, 'pending': pending, 'gone': gone}
        path = os.path.join(STATE_DIR, 'pending.json')
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False)
        os.replace(tmp, path)
        try:   # cron runs as root; the web app (sahyog) must read/write it
            import pwd
            u = pwd.getpwnam('sahyog'); os.chown(path, u.pw_uid, u.pw_gid); os.chmod(path, 0o640)
        except Exception:
            pass
        self.stdout.write(f"checked={same + len(pending) + len(gone) + errors} same={same} changed={len(pending)} gone={len(gone)} errors={errors}")
