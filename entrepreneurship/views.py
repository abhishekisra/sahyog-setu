from django.shortcuts import render

from entrepreneurship.legal_registrations.models import Legal_Registrations
from entrepreneurship.organization_registrations.models import Organization_Registration
from entrepreneurship.business_plans.models import Business_Plans
from entrepreneurship.artificial_intelligence.models import Artificial_Intelligence
from entrepreneurship.marketing.models import Marketing
from schemes.models import Schemes


def entrepreneurship_finder(request):
    """Public, no login -- Entrepreneurship Development landing/hub page in
    the Scheme Viewer's own style: a card per sub-section (each already
    rebuilt as its own *_finder.html page), replacing the old SPA landing
    page's card grid. Business Development Schemes (backed by the Schemes
    model's own business_related=1 filter, not one of the 5 sub-apps here)
    is also rebuilt as its own *_finder.html page (schemes.views.
    business_related_scheme_finder), since it shares real Schemes rows/
    detail shape with the main Scheme Viewer."""
    return render(request, "custom_admin/entrepreneurship/entrepreneurship_finder.html", {
        "total_legal_registrations": Legal_Registrations.objects.filter(status=1).count(),
        "total_organization_registrations": Organization_Registration.objects.filter(status=1).count(),
        "total_business_plans": Business_Plans.objects.filter(status=1).count(),
        "total_artificial_intelligence": Artificial_Intelligence.objects.filter(status=1).count(),
        "total_marketing": Marketing.objects.filter(status=1).count(),
        "total_business_schemes": Schemes.objects.filter(status=1, business_related=1).count(),
    })
