from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

from django.db.models import Q

from .common_tasks import validate_phone_number
User = get_user_model()


class UsernameEmailTelBackend(ModelBackend):
    """
    Custom auth backend that uses an email address or username or telephone 
    """

    def _authenticate(self, request, username=None, password=None, *args, **kwargs):
        try:
            # the tel can be +2547xxxx or 07xxx convert to an international format
            phone_no = validate_phone_number(username)
            if not phone_no:
                cur_user = User.objects.filter(Q(nickname=username)|Q(email=username)|Q(username=username)).get()
            else:
                cur_user = User.objects.filter(tel=phone_no).get()
            if cur_user.check_password(password):
                return cur_user
        except User.DoesNotExist:
            return None

    def authenticate(self, *args, **kwargs):
        return self._authenticate(*args, **kwargs)
