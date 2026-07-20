from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.backends import get_user_model
from django.db.models import Q
from .models import User

class EmailBackEnd(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(Q(Q(mobile=username) | Q(email = username))  & Q(Q(user_type = 2) | Q(user_type = 1)))
            # Hundreds of user_type=2 rows exist with password=None -- old
            # lightweight identity records the React SPA's separate
            # client_id-based user-sync endpoint (apis.user()) created for
            # site visitors who never actually signed up with a password.
            # If someone's email/mobile happens to also match one of those
            # rows (as opposed to a real admin/team login), check_password()
            # crashes trying to hash-identify a None password instead of
            # just failing the login. has_usable_password() does NOT catch
            # this -- Django's is_password_usable() only detects the
            # specific sentinel string set_unusable_password() writes, and
            # explicitly treats None as usable ("encoded is None or not
            # encoded.startswith(UNUSABLE_PASSWORD_PREFIX)"), the opposite
            # of what's needed for a genuinely empty field. Checking
            # user.password truthiness directly instead.
            if not user.password:
                return None
            if user.check_password(password):
                return user
            return None
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            # Belt-and-suspenders: mobile/mobile or email/email collisions
            # across 500+ loosely-created tracking rows aren't currently
            # possible (checked), but if one ever occurs this must still
            # fail closed rather than 500.
            return None
