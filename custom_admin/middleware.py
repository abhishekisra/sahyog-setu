from django.http import HttpResponseForbidden


# 2026-10-19 (VPS security audit): every /admin/... CRUD view (schemes, news,
# pages, banners, gallery, ...) only checks request.user.is_authenticated,
# never the role. Public users (accounts/ signup, user_type=2) and trainers
# (user_type=3) get a real Django session, so any of them could open or POST
# to admin pages directly. This closes that in one place instead of patching
# ~120 views: a logged-in non-admin gets 403 anywhere under /admin/.
# Logged-out requests are left untouched (each view already redirects them
# to the admin login page), as are the login/logout/forgot-password steps.
ADMIN_PREFIX = '/admin/'
ADMIN_OPEN_PATHS = (
    '/admin/login', '/admin/logout',
    '/admin/reset-password', '/admin/request-otp', '/admin/verify-otp',
    '/admin/change-password',
)


class AdminRoleRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith(ADMIN_PREFIX) and not path.rstrip('/').startswith(ADMIN_OPEN_PATHS):
            user = getattr(request, 'user', None)
            if user is not None and user.is_authenticated and getattr(user, 'user_type', None) != 1:
                return HttpResponseForbidden('Admin access only.')
        return self.get_response(request)
