"""ANIME URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from schemes import apis as SchemeViews
from news import apis as NewsViews
from states import apis as StatesViews
from occupations import apis as OccupationView
from testimonials import apis as TestimonialView
from banners import apis as BannerViews
from helplines import apis as HelplineView
from important_portals import apis as ImportantPortalView
from important_documents import apis as ImportantDocumentView
from scheme_announcements import apis as SchemeAnnouncementsView
from manage_gallery import apis as GalleryView
from pages import apis as PageView
from accounts import apis as UserView
from settings import apis as SettingsView
from entrepreneurship.business_plans import apis as BusinessPlans
from entrepreneurship.organization_registrations import apis as OrganizationRegistrations
from entrepreneurship.legal_registrations import apis as LegalRegistrations
from entrepreneurship.artificial_intelligence import apis as ArtificialIntelligence
from entrepreneurship.marketing import apis as Marketing
from quizzes import apis as QuizzesView

urlpatterns = [
    path('schemes-and-services', SchemeViews.schemesServices, name="schemesAndCategories"),
    path('category/<int:id>', SchemeViews.category, name="category"),
    path('schemes/central/<int:id>', SchemeViews.centralSchemes, name="centralSchemes"),
    path('schemes/state/<int:state>', SchemeViews.stateSchemes, name="centralSchemes"),
    path('schemes', SchemeViews.searchSchemes, name="searchSchemes"),
    path('scheme/<int:id>', SchemeViews.scheme, name="scheme"),
    path('states', StatesViews.states, name="states"),
    path('occupations', OccupationView.occupations, name="occupations"),
    path('testimonials', TestimonialView.testimonials, name="testimonials"),
    path('news', NewsViews.news, name="news"),
    path('banners', BannerViews.banners, name="banners"),
    path('helplines', HelplineView.helplines, name="helplines"),
    path('important-portals', ImportantPortalView.importantPortals, name="importantPortals"),
    path('scheme-announcements', SchemeAnnouncementsView.schemeAnnouncements, name="schemeAnnouncements"),
    path('important-portal/<int:id>', ImportantPortalView.importantPortal, name="importantPortal"),
    path('important-documents', ImportantDocumentView.importantDocuments, name="importantDocuments"),
    path('important-document/<int:id>', ImportantDocumentView.importantDocument, name="importantDocument"),
    path('gallery', GalleryView.gallery, name="gallery"),
    path('check-eligibility', SchemeViews.checkEligibility, name="checkEligibility"),
    path('pages', PageView.pages, name="pages"),
    path('page/<int:id>', PageView.page, name="page"),
    path('user', UserView.user, name="user"),
    path('info', SettingsView.info, name="info"),
    path('entrepreneurship-developement/business-plans', BusinessPlans.businessPlans, name="businessPlans"),
    path('entrepreneurship-developement/organization-registrations', OrganizationRegistrations.organizationRegistrations, name="organizationRegistrations"),
    path('entrepreneurship-developement/organization-registration/<int:id>', OrganizationRegistrations.organizationRegistration, name="organizationRegistration"),

    path('entrepreneurship-developement/legal-registrations', LegalRegistrations.legalRegistrations, name="legalRegistrations"),
    path('entrepreneurship-developement/legal-registration/<int:id>', LegalRegistrations.legalRegistration, name="legalRegistration"),

    path('entrepreneurship-developement/artificial-intelligence', ArtificialIntelligence.artificialIntelligence, name="artificialIntelligence"),
    path('entrepreneurship-developement/marketing', Marketing.marketing, name="marketing"),

    path('entrepreneurship/business-related-schemes', SchemeViews.businessRelatedSchemes, name="adminBusinessRelatedSchemes"),

    path('quizzes', QuizzesView.quizzes, name="quizzes"),
    path('quiz/<int:id>', QuizzesView.quiz, name="quiz"),
    path('quiz/certificate', QuizzesView.generateCertificate, name="certificate")
]