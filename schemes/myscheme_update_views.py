"""2026-11-08 (user: "myScheme monthly update"): review what changed on
myscheme.gov.in (found by `manage.py check_myscheme_updates`, monthly cron).
Approve = copy the new text into the scheme; Ignore = drop it and remember
that exact text so next month's check doesn't suggest it again."""
import json
import os
import time

from django.contrib import messages
from django.shortcuts import redirect, render

from .management.commands.check_myscheme_updates import FIELDS, STATE_DIR, _hash, _norm
from .models import Schemes

LABELS = {'title': 'Naam', 'description': 'Description', 'eligibility': 'Eligibility',
          'required_documents': 'Documents', 'mode_of_application': 'Apply kaise karein', 'web_links': 'Official links'}


def _read(name, default):
    try:
        with open(os.path.join(STATE_DIR, name), encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return default


def _write(name, data):
    p = os.path.join(STATE_DIR, name); tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, p)


def _apply(item, who, log):
    upd = {f: v for f, v in item['changed'].items() if f in FIELDS}
    if upd:
        Schemes.objects.filter(id=item['id']).update(**upd)
        log.append({'id': item['id'], 'fields': list(upd), 'by': who, 'at': int(time.time())})


def myscheme_updates(request):
    if not request.user.is_authenticated or getattr(request.user, 'user_type', None) != 1:
        return redirect('adminLogin')
    data = _read('pending.json', {'pending': [], 'gone': []})
    if request.method == 'POST':
        act = request.POST.get('act'); who = getattr(request.user, 'email', '') or str(request.user)
        log = _read('applied.json', [])
        if act == 'approve_all':
            for it in data['pending']:
                _apply(it, who, log)
            n = len(data['pending']); data['pending'] = []
            messages.success(request, f'{n} schemes update ho gayi.')
        else:
            try:
                sid = int(request.POST.get('id'))
            except (TypeError, ValueError):
                return redirect('myscheme_updates')
            it = next((x for x in data['pending'] if x['id'] == sid), None)
            if it and act == 'approve':
                _apply(it, who, log); messages.success(request, f'Scheme {sid} update ho gayi.')
            elif it and act == 'ignore':
                ign = _read('ignored.json', {})
                ign.setdefault(str(sid), {}).update({f: _hash(v) for f, v in it['changed'].items()})
                _write('ignored.json', ign); messages.info(request, f'Scheme {sid}: badlav ignore kiya.')
            data['pending'] = [x for x in data['pending'] if x['id'] != sid]
        _write('pending.json', data); _write('applied.json', log)
        return redirect('myscheme_updates')
    rows = []
    for it in data.get('pending', []):
        rows.append({'id': it['id'], 'title': it['title'], 'status': it.get('status'),
                     'fields': [{'label': LABELS.get(f, f), 'old': _norm(it['old'].get(f, ''))[:500],
                                 'new': _norm(v)[:500]} for f, v in it['changed'].items()]})
    return render(request, 'custom_admin/schemes/myscheme_updates.html', {
        'rows': rows, 'gone': data.get('gone', []), 'checked_at': data.get('checked_at'),
        'same': data.get('same'), 'errors': data.get('errors')})
