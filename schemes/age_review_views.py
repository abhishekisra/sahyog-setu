"""2026-11-08 (user: "2 karo"): admin screen to fill missing scheme ages.

91% of active schemes had no age (stored 0-100). age_extract.py reads a
suggestion from the eligibility text; NOTHING is saved until an admin
approves it here. Approved ages feed the eligibility check, "Schemes for
me" and upliftdata.cloud (which reads ages from /api/scheme/<id>).
Rejected suggestions are remembered in a private file (not web-served)."""
import json
import os
import time

from django.contrib import messages
from django.shortcuts import redirect, render

from .age_extract import extract
from .models import Schemes

STATE = os.environ.get('SAHYOG_AGE_REVIEW_FILE', '/var/lib/sahyogsetu/age_review/state.json')


def _state():
    try:
        with open(STATE, encoding='utf-8') as f:
            d = json.load(f)
    except (FileNotFoundError, ValueError):
        d = {}
    d.setdefault('rejected', []); d.setdefault('log', [])
    return d


def _save_state(d):
    tmp = STATE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, STATE)


def _suggestions(rejected):
    out = []
    for s in Schemes.objects.filter(status=1, age_min=0, age_max__gte=100).only('id', 'title', 'eligibility', 'scheme_type', 'state_id'):
        if s.id in rejected:
            continue
        x = extract(s.eligibility)
        if x:
            out.append({'id': s.id, 'title': s.title, 'central': s.scheme_type == 0, **x})
    out.sort(key=lambda r: (r['confidence'] != 'check', not r['central'], r['id']))
    return out


def age_review(request):
    # same rule as the other admin screens: logged out -> login page; a logged-in
    # non-admin is already refused by AdminRoleRequiredMiddleware (403)
    if not request.user.is_authenticated or getattr(request.user, 'user_type', None) != 1:
        return redirect('adminLogin')
    st = _state()
    rejected = set(st['rejected'])
    if request.method == 'POST':
        act = request.POST.get('act')
        who = getattr(request.user, 'email', '') or str(request.user)
        if act == 'approve_good':
            n = 0
            for r in _suggestions(rejected):
                if r['confidence'] == 'good':
                    Schemes.objects.filter(id=r['id'], age_min=0, age_max__gte=100).update(age_min=r['min'], age_max=r['max'])
                    st['log'].append({'id': r['id'], 'min': r['min'], 'max': r['max'], 'by': who, 'at': int(time.time()), 'how': 'approve all good'})
                    n += 1
            _save_state(st)
            messages.success(request, f'{n} schemes ki age save ho gayi.')
        else:
            try:
                sid = int(request.POST.get('id'))
            except (TypeError, ValueError):
                return redirect('scheme_age_review')
            if act == 'reject':
                st['rejected'] = sorted(rejected | {sid}); _save_state(st)
                messages.info(request, f'Scheme {sid}: suggestion hata di.')
            elif act == 'approve':
                try:
                    mn = int(request.POST.get('min') or 0); mx = int(request.POST.get('max') or 100)
                except ValueError:
                    messages.error(request, 'Age number mein likhein.'); return redirect('scheme_age_review')
                if not (0 <= mn < mx <= 100):
                    messages.error(request, 'Min age, max age se kam honi chahiye (0-100).'); return redirect('scheme_age_review')
                Schemes.objects.filter(id=sid).update(age_min=mn, age_max=mx)
                st['log'].append({'id': sid, 'min': mn, 'max': mx, 'by': who, 'at': int(time.time()), 'how': 'approve'})
                _save_state(st)
                messages.success(request, f'Scheme {sid}: age {mn}-{mx} save ho gayi.')
        return redirect('scheme_age_review')
    rows = _suggestions(rejected)
    left = Schemes.objects.filter(status=1, age_min=0, age_max__gte=100).count()
    return render(request, 'custom_admin/schemes/age_review.html', {
        'rows': rows, 'good': sum(1 for r in rows if r['confidence'] == 'good'),
        'check': sum(1 for r in rows if r['confidence'] == 'check'), 'left': left,
        'approved': len(st['log']), 'rejected': len(rejected)})
