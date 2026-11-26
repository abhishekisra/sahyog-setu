import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from accounts.models import User
from .models import Settings

def info(request):
    users = len(User.objects.all())
    info_settings = Settings.objects.all()
    last_updated =""
    if info_settings[1].info:
        users = users + int(info_settings[1].info)

    if info_settings[0].info:
        last_updated = info_settings[0].info
    # 2026-11-26 (user: easy to use -> "sab sahi karo"): the footer showed a hand-typed date that was never changed
    # ("20 February, 2026"). Show the newest real content date (schemes / announcements), or the typed date if newer.
    try:
        from django.db.models import Max
        from schemes.models import Schemes
        dates = [Schemes.objects.aggregate(m=Max('updated_at'))['m'], Schemes.objects.aggregate(m=Max('created_at'))['m']]
        try:
            import scheme_announcements.models as _SA
            for _n in dir(_SA):
                _M = getattr(_SA, _n)
                if hasattr(_M, '_meta') and getattr(_M._meta, 'app_label', '') == 'scheme_announcements' and any(f.name == 'created_at' for f in _M._meta.fields):
                    dates.append(_M.objects.aggregate(m=Max('created_at'))['m'])
        except Exception:
            pass
        best = max((d for d in dates if d), default=None)
        typed = None
        try:
            typed = datetime.datetime.strptime(str(last_updated).strip(), '%d %B, %Y')
        except ValueError:
            pass
        if best and (not typed or best.date() > typed.date()):
            last_updated = best.strftime('%d %B, %Y').lstrip('0')
    except Exception:
        pass
    return JsonResponse({'visitors' : users, 'last_updated' : last_updated, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)