"""Popularity: count real opens of a scheme / Important Portal (2026-11-25, user: "jo jyada popular
wo jayda upar ... important portal ke andar jo portal jayada check wo first").

record_open() is called from the public detail APIs (/api/scheme/<id>, /api/important-portal/<id>),
which every viewer page calls when a person opens an item. One count per visitor per item per day
(ContentOpen unique row); search-engine and other bots are skipped. Never raises -- a counting
problem must not break the page."""
import datetime
import hashlib
import re

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F

BOT_RE = re.compile(r'bot|crawl|spider|slurp|facebookexternalhit|meta-external|preview|headless|python|curl|wget|'
                    r'httpclient|okhttp|scrapy|lighthouse|monitor', re.I)


def _visitor(request):
    ip = (request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR') or '').split(',')[0].strip()
    ua = request.META.get('HTTP_USER_AGENT', '')
    return hashlib.sha256((settings.SECRET_KEY + '|' + ip + '|' + ua).encode()).hexdigest()[:32]


def popular_order(qs):
    """Most opened first (real opens + starting score), then newest."""
    return qs.annotate(_pop=F('open_count') + F('seed_score')).order_by('-_pop', '-id')


def record_open(request, kind, model, obj_id):
    try:
        ua = request.META.get('HTTP_USER_AGENT', '')
        if not ua or BOT_RE.search(ua):
            return
        if request.user.is_authenticated and request.user.is_staff:
            return  # admins checking content are not "popularity"
        from schemes.models import ContentOpen
        with transaction.atomic():
            ContentOpen.objects.create(kind=kind, obj_id=obj_id, visitor=_visitor(request),
                                       day=datetime.date.today())
            model.objects.filter(id=obj_id).update(open_count=F('open_count') + 1)
    except IntegrityError:
        pass  # already counted today for this visitor
    except Exception:
        pass
