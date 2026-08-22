from django.urls import path

from .import views
from django.conf.urls.static import static
from django.conf import settings

from occupations import views as Occupations
from schemes import views as Schemes
from important_portals import views as ImportantPortals
from testimonials import views as Testimonials
from news import views as News
from helplines import views as Helplines
from banners import views as Banners
from important_documents import views as ImportantDocuments
from scheme_announcements import views as SchemeAnnouncements
from manage_gallery import views as Gallery
from pages import views as Pages
from accounts import views as UserView
from settings import views as Settings
from entrepreneurship.business_plans import views as BusinessPlans
from entrepreneurship.organization_registrations import views as OrganizationRegistrations
from entrepreneurship.legal_registrations import views as LegalRegistrations
from entrepreneurship.artificial_intelligence import views as ArtificialIntelligence
from entrepreneurship.marketing import views as Marketing
from quizzes import views as Quizzes
from partners import views as Partners
from states import views as States

urlpatterns = [

    path('login', views.LoginView.as_view(), name="adminLogin"),
    path('logout', views.LogoutView.as_view(), name="adminLogout"),
    path('dashboard', views.dashboard, name="adminDashboard"),   

    path('news', News.NewsView.as_view(), name="adminNews"),
    path('news/<int:id>', News.updateNews, name="adminUpdateNews"),
    path('news/delete', News.deleteNews, name="adminDeleteNews"),
    path('news/<int:id>/translations', News.NewsTranslationsView.as_view(), name="adminNewsTranslations"),
    path('news/<int:id>/translations/<str:lang>', News.NewsEditTranslationView.as_view(), name="adminNewsEditTranslation"),

    path('occupations', Occupations.OccupationsView.as_view(), name="adminOccupations"),
    path('states-translations', States.states_translations_hub, name="adminStatesTranslationsHub"),
    path('state/<int:id>/translations', States.StateTranslationsView.as_view(), name="adminStateTranslations"),
    path('state/<int:id>/translations/<str:lang>', States.StateEditTranslationView.as_view(), name="adminStateEditTranslation"),
    path('districts-translations', States.districts_translations_hub, name="adminDistrictsTranslationsHub"),
    path('district/<int:id>/translations', States.DistrictTranslationsView.as_view(), name="adminDistrictTranslations"),
    path('district/<int:id>/translations/<str:lang>', States.DistrictEditTranslationView.as_view(), name="adminDistrictEditTranslation"),
    path('occupation/<int:id>', Occupations.updateOccupation, name="adminUpdateOccupation"),
    path('occupation/delete', Occupations.deleteOccupation, name="adminDeleteOccupation"),
    path('occupation/<int:id>/translations', Occupations.OccupationTranslationsView.as_view(), name="adminOccupationTranslations"),
    path('occupation/<int:id>/translations/<str:lang>', Occupations.OccupationEditTranslationView.as_view(), name="adminOccupationEditTranslation"),

    path('manage-schemes/categories', Schemes.CategoriesView.as_view(), name="adminSchemeCategories"),
    path('manage-schemes/category/<int:id>', Schemes.updateCategory, name="updateAdminCategory"),
    path('manage-schemes/category/delete', Schemes.deleteCategory, name="adminDeleteCategory"),
    path('manage-schemes/category/<int:id>/translations', Schemes.CategoryTranslationsView.as_view(), name="adminCategoryTranslations"),
    path('manage-schemes/category/<int:id>/translations/<str:lang>', Schemes.CategoryEditTranslationView.as_view(), name="adminCategoryEditTranslation"),

    path('manage-schemes/schemes', Schemes.SchemesView.as_view(),name="adminSchemes"),
    path('manage-schemes/scheme', Schemes.SchemeView.as_view(),name="adminNewScheme"),
    path('manage-schemes/scheme/<int:id>', Schemes.EditSchemeView.as_view(),name="adminEditScheme"),
    path('manage-schemes/scheme/delete', Schemes.deleteScheme, name="adminDeleteScheme"),
    path('manage-schemes/schemes/bulk-activate', Schemes.BulkActivateSchemesView.as_view(), name="adminBulkActivateSchemes"),
    path('manage-schemes/scheme/<int:id>/preview', Schemes.admin_scheme_detail, name="adminSchemeDetail"),
    path('manage-schemes/scheme/<int:id>/translations', Schemes.SchemeTranslationsView.as_view(), name="adminSchemeTranslations"),
    path('manage-schemes/scheme/<int:id>/translations/<str:lang>', Schemes.SchemeEditTranslationView.as_view(), name="adminSchemeEditTranslation"),

    path('important-documents', ImportantDocuments.ImportantDocumentsView.as_view(),name="adminImportantDocuments"),
    path('important-document', ImportantDocuments.ImportantDocumentView.as_view(),name="adminNewImportantDocument"),
    path('important-document/<int:id>', ImportantDocuments.EditImportantDocumentView.as_view(),name="adminEditImportantDocument"),
    path('important-document/delete', ImportantDocuments.deleteImportantDocument, name="adminDeleteImportantDocument"),
    path('important-document/<int:id>/preview', ImportantDocuments.admin_document_detail, name="adminDocumentDetail"),
    path('important-document/<int:id>/translations', ImportantDocuments.ImportantDocumentTranslationsView.as_view(), name="adminImportantDocumentTranslations"),
    path('important-document/<int:id>/translations/<str:lang>', ImportantDocuments.ImportantDocumentEditTranslationView.as_view(), name="adminImportantDocumentEditTranslation"),

    path('important-portals', ImportantPortals.ImportantPortalsView.as_view(),name="adminImportantPotals"),
    path('important-portal', ImportantPortals.ImportantPortalView.as_view(),name="adminNewImportantPortal"),
    path('important-portal/<int:id>', ImportantPortals.EditImportantPortalView.as_view(),name="adminEditImportantPortal"),
    path('important-portal/delete', ImportantPortals.deleteImportantPortal, name="adminDeleteImportantPortal"),
    path('important-portal/<int:id>/preview', ImportantPortals.admin_portal_detail, name="adminPortalDetail"),
    path('important-portal/<int:id>/translations', ImportantPortals.ImportantPortalTranslationsView.as_view(), name="adminImportantPortalTranslations"),
    path('important-portal/<int:id>/translations/<str:lang>', ImportantPortals.ImportantPortalEditTranslationView.as_view(), name="adminImportantPortalEditTranslation"),

    path('testimonials', Testimonials.TestimonialsView.as_view(), name="adminTestimonials"),
    path('testimonial/delete', Testimonials.deleteTestimonial, name="adminDeleteTestimonial"),
    path('testimonial/<int:id>', Testimonials.updateTestimonial, name="adminUpdateTestimonial"),

    path('helplines', Helplines.HelplinesView.as_view(), name="adminHelplines"),
    path('helpline/delete', Helplines.deleteHelpline, name="adminDeleteHelpline"),
    path('helpline/<int:id>', Helplines.updateHelpline, name="adminUpdateHelpline"),
    path('helpline/<int:id>/translations', Helplines.HelplineTranslationsView.as_view(), name="adminHelplineTranslations"),
    path('helpline/<int:id>/translations/<str:lang>', Helplines.HelplineEditTranslationView.as_view(), name="adminHelplineEditTranslation"),

    path('scheme-announcements', SchemeAnnouncements.SchemeAnnouncementsView.as_view(), name="adminSchemeAnnouncements"),
    path('scheme-announcement/delete', SchemeAnnouncements.deleteSchemeAnnouncement, name="adminDeleteSchemeAnnouncements"),
    path('scheme-announcement/<int:id>', SchemeAnnouncements.updateSchemeAnnouncement, name="adminUpdateSchemeAnnouncements"),
    path('scheme-announcement/<int:id>/translations', SchemeAnnouncements.SchemeAnnouncementTranslationsView.as_view(), name="adminSchemeAnnouncementTranslations"),
    path('scheme-announcement/<int:id>/translations/<str:lang>', SchemeAnnouncements.SchemeAnnouncementEditTranslationView.as_view(), name="adminSchemeAnnouncementEditTranslation"),

    path('banners', Banners.BannerView.as_view(), name="adminBanners"),
    path('banner/delete', Banners.deleteBanner, name="adminDeleteBanners"),
    path('banner/<int:id>', Banners.updateBanner, name="adminUpdateBanners"),

    path('manage-gallery/images', Gallery.ImageView.as_view(), name="adminGalleryImages"),
    path('manage-gallery/image/delete', Gallery.deleteImage, name="adminDeleteGalleryImage"),
    path('manage-gallery/image/<int:id>', Gallery.updateImage, name="adminUpdateGalleryImage"),

    path('manage-gallery/videoes', Gallery.VideoView.as_view(), name="adminGalleryVideoes"),
    path('manage-gallery/video/delete', Gallery.deleteVideo, name="adminDeleteGalleryVideo"),
    path('manage-gallery/video/<int:id>', Gallery.updateVideo, name="adminUpdateGalleryVideo"),

    path('pages', Pages.PagesView.as_view(),name="adminPages"),
    path('page', Pages.PageView.as_view(),name="adminNewPage"),
    path('page/<int:id>', Pages.EditPageView.as_view(),name="adminEditPage"),
    path('page/delete', Pages.deletePage, name="adminDeletePage"),
    path('page/<int:id>/translations', Pages.PageTranslationsView.as_view(), name="adminPageTranslations"),
    path('page/<int:id>/translations/<str:lang>', Pages.PageEditTranslationView.as_view(), name="adminPageEditTranslation"),

    path('visitors', UserView.visitors, name="adminVisitors"),

    path('settings', Settings.SettingsView.as_view(), name="adminSettings"),   
    path('settings/<int:id>', Settings.updateSettings, name="adminUpdateSettings"),

    path('entrepreneurship/business-plans', BusinessPlans.BusinessPlansView.as_view(), name="adminBusinessPlans"),
    path('entrepreneurship/business-plan/delete', BusinessPlans.deleteBusinessPlan, name="adminDeleteBusinessPlan"),
    path('entrepreneurship/business-plan/<int:id>', BusinessPlans.updateBusinessPlan, name="adminUpdateBusinessPlan"),
    path('entrepreneurship/business-plan/<int:id>/translations', BusinessPlans.BusinessPlanTranslationsView.as_view(), name="adminBusinessPlanTranslations"),
    path('entrepreneurship/business-plan/<int:id>/translations/<str:lang>', BusinessPlans.BusinessPlanEditTranslationView.as_view(), name="adminBusinessPlanEditTranslation"),

    path('entrepreneurship/organizations-registrations', OrganizationRegistrations.OrganizationRegistrationsView.as_view(), name="adminOrganizationRegistrations"),
    path('entrepreneurship/organization-registration', OrganizationRegistrations.OrganizationRegistrationView.as_view(), name="adminOrganizationRegistration"),
    path('entrepreneurship/organization-registration/delete', OrganizationRegistrations.deleteOrganizationRegistration, name="adminDeleteOrganizationRegistration"),
    path('entrepreneurship/organization-registration/<int:id>', OrganizationRegistrations.EditOrganizationRegistrationView.as_view(), name="adminUpdateOrganizationRegistrations"),
    path('entrepreneurship/organization-registration/<int:id>/preview', OrganizationRegistrations.admin_organization_registration_detail, name="adminOrganizationRegistrationDetail"),
    path('entrepreneurship/organization-registration/<int:id>/translations', OrganizationRegistrations.OrganizationRegistrationTranslationsView.as_view(), name="adminOrganizationRegistrationTranslations"),
    path('entrepreneurship/organization-registration/<int:id>/translations/<str:lang>', OrganizationRegistrations.OrganizationRegistrationEditTranslationView.as_view(), name="adminOrganizationRegistrationEditTranslation"),

    path('entrepreneurship/legal-registrations', LegalRegistrations.LegalRegistrationsView.as_view(), name="adminLegalRegistrations"),
    path('entrepreneurship/legal-registration', LegalRegistrations.LegalRegistrationView.as_view(), name="adminLegalRegistration"),
    path('entrepreneurship/legal-registration/delete', LegalRegistrations.deleteLegalRegistration, name="adminDeleteLegalRegistration"),
    path('entrepreneurship/legal-registration/<int:id>', LegalRegistrations.EditLegalRegistrationView.as_view(), name="adminUpdateLegalRegistrations"),
    path('entrepreneurship/legal-registration/<int:id>/preview', LegalRegistrations.admin_legal_registration_detail, name="adminLegalRegistrationDetail"),
    path('entrepreneurship/legal-registration/<int:id>/translations', LegalRegistrations.LegalRegistrationTranslationsView.as_view(), name="adminLegalRegistrationTranslations"),
    path('entrepreneurship/legal-registration/<int:id>/translations/<str:lang>', LegalRegistrations.LegalRegistrationEditTranslationView.as_view(), name="adminLegalRegistrationEditTranslation"),

    path('entrepreneurship/artificial-intelligence', ArtificialIntelligence.ArtificialIntelligenceView.as_view(), name="adminArtificialIntelligence"),
    path('entrepreneurship/artificial-intelligence/delete', ArtificialIntelligence.deleteArtificialIntelligence, name="adminDeleteArtificialIntelligence"),
    path('entrepreneurship/artificial-intelligence/<int:id>', ArtificialIntelligence.updateArtificialIntelligence, name="adminUpdateArtificialIntelligence"),
    path('entrepreneurship/artificial-intelligence/<int:id>/translations', ArtificialIntelligence.ArtificialIntelligenceTranslationsView.as_view(), name="adminArtificialIntelligenceTranslations"),
    path('entrepreneurship/artificial-intelligence/<int:id>/translations/<str:lang>', ArtificialIntelligence.ArtificialIntelligenceEditTranslationView.as_view(), name="adminArtificialIntelligenceEditTranslation"),

    path('entrepreneurship/marketing', Marketing.MarketingView.as_view(), name="adminMarketing"),
    path('entrepreneurship/marketing/delete', Marketing.deleteMarketing, name="adminDeleteMarketing"),
    path('entrepreneurship/marketing/<int:id>', Marketing.updateMarketing, name="adminUpdateMarketing"),
    path('entrepreneurship/marketing/<int:id>/translations', Marketing.MarketingTranslationsView.as_view(), name="adminMarketingTranslations"),
    path('entrepreneurship/marketing/<int:id>/translations/<str:lang>', Marketing.MarketingEditTranslationView.as_view(), name="adminMarketingEditTranslation"),

    path('quizzes', Quizzes.QuizzesView.as_view(),name="adminQuizzes"),
    path('quiz', Quizzes.QuizView.as_view(),name="adminNewQuiz"),
    path('quiz/<int:id>', Quizzes.EditQuizView.as_view(),name="adminEditQuiz"),
    path('quiz/delete', Quizzes.deleteQuiz, name="adminDeleteQuiz"),
    path('quiz/<int:id>/import-questions', Quizzes.ImportQuestionsView.as_view(), name="adminImportQuestions"),
    path('quiz/import-questions/template', Quizzes.download_question_template, name="adminImportQuestionsTemplate"),
    path('quiz/<int:id>/generate-questions', Quizzes.GenerateQuestionsView.as_view(), name="adminGenerateQuestions"),
    path('quiz/generate-explanation', Quizzes.GenerateExplanationView.as_view(), name="adminGenerateExplanation"),
    path('quiz/<int:id>/review-generated-questions', Quizzes.ReviewGeneratedQuestionsView.as_view(), name="adminReviewGeneratedQuestions"),
    path('quiz/<int:id>/translations', Quizzes.QuizTranslationsView.as_view(), name="adminQuizTranslations"),
    path('quiz/<int:id>/translations/<str:lang>', Quizzes.EditTranslationView.as_view(), name="adminEditTranslation"),

    path('partners', Partners.ManagePartnersView.as_view(), name="adminManagePartners"),
    path('partner/<int:id>', Partners.updatePartner, name="adminUpdatePartner"),
    path('partner/toggle-active', Partners.togglePartnerActive, name="adminTogglePartnerActive"),



] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)