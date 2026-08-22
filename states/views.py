from django.shortcuts import render, redirect
from django.contrib import messages

from .models import States, District, StateTranslation, DistrictTranslation
from custom_admin.translation_views import TranslationsPickerView, EditTranslationView

# Create your views here.


def states_translations_hub(request):
    """Minimal read-only list of States, purely as an entry point into the
    Translations flow -- there is no existing admin CRUD for States/District
    anywhere in this codebase (no admin.py registration, no custom_admin
    views, no states/urls.py at all; only ever read via states/apis.py for
    the signup dropdown and scheme_finder's state filter), so this page
    isn't replacing/duplicating anything. Deliberately does not add
    add/edit/delete for the states/districts themselves -- that CRUD gap
    is out of scope here, this is translations-only."""
    if not request.user.is_authenticated:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
    states = States.objects.all().order_by('state')
    return render(request, 'custom_admin/states/states_translations_hub.html', {'states': states})


class StateTranslationsView(TranslationsPickerView):
    model = States
    translation_model = StateTranslation
    fk_name = "state"
    fields = ["state_name"]
    object_label = "state"
    list_url_name = "adminStatesTranslationsHub"
    list_label = "States"
    edit_url_name = "adminStateEditTranslation"


class StateEditTranslationView(EditTranslationView):
    model = States
    translation_model = StateTranslation
    fk_name = "state"
    fields = [("state_name", "State Name", "text")]
    object_label = "state"
    picker_url_name = "adminStateTranslations"


def districts_translations_hub(request):
    """Flat list of every District across every state, purely as an entry
    point into the Translations flow -- same reasoning as
    states_translations_hub above (no existing admin CRUD for District
    either, only ever read via the signup form's state-filtered AJAX
    dropdown). Flat rather than nested under each state's own page because
    TranslationsPickerView's picker.html "back to list" link
    ({% url list_url_name %}) takes no arguments -- a single, DataTable-
    searchable table (763 rows) is simpler than adding per-state URL
    scoping to the generic view just for this one app."""
    if not request.user.is_authenticated:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
    districts = District.objects.select_related('state').order_by('state__state', 'name')
    return render(request, 'custom_admin/states/districts_translations_hub.html', {'districts': districts})


class DistrictTranslationsView(TranslationsPickerView):
    model = District
    translation_model = DistrictTranslation
    fk_name = "district"
    fields = ["name"]
    object_label = "name"
    list_url_name = "adminDistrictsTranslationsHub"
    list_label = "Districts"
    edit_url_name = "adminDistrictEditTranslation"


class DistrictEditTranslationView(EditTranslationView):
    model = District
    translation_model = DistrictTranslation
    fk_name = "district"
    fields = [("name", "District Name", "text")]
    object_label = "name"
    picker_url_name = "adminDistrictTranslations"
