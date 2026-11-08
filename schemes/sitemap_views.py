"""2026-11-08 (user: "4 karo" -- Google visibility): one sitemap entry per
active scheme. The static /sitemap.xml (nginx, /var/www/html) lists only the
18 section pages, so Google never found the 4,653 scheme pages even though
each already has its own <title>, description and canonical URL
(/scheme-viewer/?scheme=<id>, see views.scheme_finder). Built from the
database on each request (cached 6 h), so new / edited schemes appear on
their own. robots.txt points to it."""
from django.http import HttpResponse
from django.views.decorators.cache import cache_page

from .models import Schemes

BASE = 'https://sahyogsetu.in'


@cache_page(6 * 3600)
def sitemap_schemes(request):
    rows = (Schemes.objects.filter(status=1).order_by('id').values_list('id', 'updated_at'))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for sid, upd in rows:
        lm = f'<lastmod>{upd.date().isoformat()}</lastmod>' if upd else ''
        out.append(f'  <url><loc>{BASE}/scheme-viewer/?scheme={sid}</loc>{lm}<priority>0.6</priority></url>')
    out.append('</urlset>')
    return HttpResponse('\n'.join(out) + '\n', content_type='application/xml; charset=utf-8')
