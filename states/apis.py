import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import StateSerializer
from .models import States
from languages.utils import clean_language


def _state_label(s, lang):
    """States.state (content field) vs StateTranslation.state_name
    (translation field) are deliberately different names -- 'state' was
    already taken by the FK on Schemes/District pointing at this model, so
    TranslatableMixin.field_for('state', lang) can't be used directly here
    (it would look for a non-existent `state` attribute on the translation
    row and silently fall back to English every time)."""
    if lang == "en":
        return s.state
    t = s._translation(lang)
    return (t.state_name if t and t.state_name else s.state)


def states(request):
    # Optional ?lang= -- absent (the untouched legacy SPA never sends it)
    # gives byte-identical output to before.
    states = list(States.objects.all())
    serializer = StateSerializer(states, many=True)
    data = serializer.data
    lang = clean_language(request.GET.get('lang', 'en'))
    if lang != 'en':
        data = [dict(d, label=_state_label(s, lang)) for d, s in zip(data, states)]
    return JsonResponse({'states' : data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


