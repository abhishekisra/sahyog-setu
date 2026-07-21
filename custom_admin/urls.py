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

urlpatterns = [

    path('login', views.LoginView.as_view(), name="adminLogin"),
    path('logout', views.LogoutView.as_view(), name="adminLogout"),
    path('dashboard', views.dashboard, name="adminDashboard"),   

    path('news', News.NewsView.as_view(), name="adminNews"),   
    path('news/<int:id>', News.updateNews, name="adminUpdateNews"),
    path('news/delete', News.deleteNews, name="adminDeleteNews"),

    path('occupations', Occupations.OccupationsView.as_view(), name="adminOccupations"),   
    path('occupation/<int:id>', Occupations.updateOccupation, name="adminUpdateOccupation"),
    path('occupation/delete', Occupations.deleteOccupation, name="adminDeleteOccupation"),

    path('manage-schemes/categories', Schemes.CategoriesView.as_view(), name="adminSchemeCategories"),
    path('manage-schemes/category/<int:id>', Schemes.updateCategory, name="updateAdminCategory"),
    path('manage-schemes/category/delete', Schemes.deleteCategory, name="adminDeleteCategory"),

    path('manage-schemes/schemes', Schemes.SchemesView.as_view(),name="adminSchemes"),
    path('manage-schemes/scheme', Schemes.SchemeView.as_view(),name="adminNewScheme"),
    path('manage-schemes/scheme/<int:id>', Schemes.EditSchemeView.as_view(),name="adminEditScheme"),
    path('manage-schemes/scheme/delete', Schemes.deleteScheme, name="adminDeleteScheme"),
    path('manage-schemes/schemes/bulk-activate', Schemes.BulkActivateSchemesView.as_view(), name="adminBulkActivateSchemes"),

    path('important-documents', ImportantDocuments.ImportantDocumentsView.as_view(),name="adminImportantDocuments"),
    path('important-document', ImportantDocuments.ImportantDocumentView.as_view(),name="adminNewImportantDocument"),
    path('important-document/<int:id>', ImportantDocuments.EditImportantDocumentView.as_view(),name="adminEditImportantDocument"),
    path('important-document/delete', ImportantDocuments.deleteImportantDocument, name="adminDeleteImportantDocument"),

    path('important-portals', ImportantPortals.ImportantPortalsView.as_view(),name="adminImportantPotals"),
    path('important-portal', ImportantPortals.ImportantPortalView.as_view(),name="adminNewImportantPortal"),
    path('important-portal/<int:id>', ImportantPortals.EditImportantPortalView.as_view(),name="adminEditImportantPortal"),
    path('important-portal/delete', ImportantPortals.deleteImportantPortal, name="adminDeleteImportantPortal"),

    path('testimonials', Testimonials.TestimonialsView.as_view(), name="adminTestimonials"),
    path('testimonial/delete', Testimonials.deleteTestimonial, name="adminDeleteTestimonial"),
    path('testimonial/<int:id>', Testimonials.updateTestimonial, name="adminUpdateTestimonial"),

    path('helplines', Helplines.HelplinesView.as_view(), name="adminHelplines"),
    path('helpline/delete', Helplines.deleteHelpline, name="adminDeleteHelpline"),
    path('helpline/<int:id>', Helplines.updateHelpline, name="adminUpdateHelpline"),

    path('scheme-announcements', SchemeAnnouncements.SchemeAnnouncementsView.as_view(), name="adminSchemeAnnouncements"),
    path('scheme-announcement/delete', SchemeAnnouncements.deleteSchemeAnnouncement, name="adminDeleteSchemeAnnouncements"),
    path('scheme-announcement/<int:id>', SchemeAnnouncements.updateSchemeAnnouncement, name="adminUpdateSchemeAnnouncements"),

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

    path('visitors', UserView.visitors, name="adminVisitors"),

    path('settings', Settings.SettingsView.as_view(), name="adminSettings"),   
    path('settings/<int:id>', Settings.updateSettings, name="adminUpdateSettings"),

    path('entrepreneurship/business-plans', BusinessPlans.BusinessPlansView.as_view(), name="adminBusinessPlans"),
    path('entrepreneurship/business-plan/delete', BusinessPlans.deleteBusinessPlan, name="adminDeleteBusinessPlan"),
    path('entrepreneurship/business-plan/<int:id>', BusinessPlans.updateBusinessPlan, name="adminUpdateBusinessPlan"),

    path('entrepreneurship/organizations-registrations', OrganizationRegistrations.OrganizationRegistrationsView.as_view(), name="adminOrganizationRegistrations"),
    path('entrepreneurship/organization-registration', OrganizationRegistrations.OrganizationRegistrationView.as_view(), name="adminOrganizationRegistration"),
    path('entrepreneurship/organization-registration/delete', OrganizationRegistrations.deleteOrganizationRegistration, name="adminDeleteOrganizationRegistration"),
    path('entrepreneurship/organization-registration/<int:id>', OrganizationRegistrations.EditOrganizationRegistrationView.as_view(), name="adminUpdateOrganizationRegistrations"),

    path('entrepreneurship/legal-registrations', LegalRegistrations.LegalRegistrationsView.as_view(), name="adminLegalRegistrations"),
    path('entrepreneurship/legal-registration', LegalRegistrations.LegalRegistrationView.as_view(), name="adminLegalRegistration"),
    path('entrepreneurship/legal-registration/delete', LegalRegistrations.deleteLegalRegistration, name="adminDeleteLegalRegistration"),
    path('entrepreneurship/legal-registration/<int:id>', LegalRegistrations.EditLegalRegistrationView.as_view(), name="adminUpdateLegalRegistrations"),

    path('entrepreneurship/artificial-intelligence', ArtificialIntelligence.ArtificialIntelligenceView.as_view(), name="adminArtificialIntelligence"),
    path('entrepreneurship/artificial-intelligence/delete', ArtificialIntelligence.deleteArtificialIntelligence, name="adminDeleteArtificialIntelligence"),
    path('entrepreneurship/artificial-intelligence/<int:id>', ArtificialIntelligence.updateArtificialIntelligence, name="adminUpdateArtificialIntelligence"),

    path('entrepreneurship/marketing', Marketing.MarketingView.as_view(), name="adminMarketing"),
    path('entrepreneurship/marketing/delete', Marketing.deleteMarketing, name="adminDeleteMarketing"),
    path('entrepreneurship/marketing/<int:id>', Marketing.updateMarketing, name="adminUpdateMarketing"),

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