from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError

from mspark_whatsapp_analyzer import settings
from users.managers import CustomUserManager


class User(AbstractUser):
    REQUIRED_FIELDS = ['email']
    objects = CustomUserManager()


    email = models.EmailField(unique=True, null=True,
                              help_text=_('Should be email'))
    member_id = models.ForeignKey('members.GroupMember', on_delete=models.DO_NOTHING, related_name='user_member_id', null=True)

    def __str__(self):
        return self.email if self.email else 'No Email Provided'

    def get_full_name(self) -> str:
        return self.first_name + ' ' + self.last_name

    def get_short_name(self):
        return self.email

    def clean(self, *args, **kwargs):
        """
        Clean data
        """
        # check same username and email are provided
        if not self.username == self.email:
            raise ValidationError('Provide same username and email')


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Auto create user tokens on new user creation
    """
    if created:
        Token.objects.create(user=instance).save()