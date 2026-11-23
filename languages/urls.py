from django.urls import path

from . import views_i18n as v

urlpatterns = [
    path("api/site-languages", v.site_languages),
    path("i18n-job/<str:token>/notebook.ipynb", v.notebook),
    path("i18n-job/<str:token>/<str:job>/manifest.json", v.manifest),
    path("i18n-job/<str:token>/<str:job>/done.json", v.done),
    path("i18n-job/<str:token>/<str:job>/chunk/<int:n>.json", v.chunk),
    path("i18n-job/<str:token>/<str:job>/result/<str:lang>/<int:n>", v.result),
]
