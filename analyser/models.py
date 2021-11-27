import datetime

from enum import Enum
from django.db import models
from django.db.models.signals import post_save
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator, RegexValidator, MaxLengthValidator, MinLengthValidator, MaxValueValidator, MinValueValidator
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

settings.TIME_ZONE

"""
    We define user access control groups here
"""

PERSONNEL_DESIGNATION_CHOICES = (
    ('data_manager', 'Data Manager'),
    ('system_admin', 'System Administrator'),
    ('business_counselor', 'Business Counselor'),
    ('business_advisor', 'Business Advisor'),
    ('program_manager', 'Program Manager'),
)

PERSONNEL_GENDER_CHOICES = (
    ('male', 'Male'),
    ('female', 'Female'),
)

STATUS_CHOICES = (
    ('processed', 'Processed'),
    ('pending', 'Pending'),
    ('failed', 'Failed Processing'),
    ('failed_preprocessing', 'Failed Pre Processing'),
    ('to_reprocess', 'Reprocess'),
)

PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+254 7xx xxx xxx'. Up to 15 digits allowed.")


class TimeModel(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Personnel(AbstractUser):
    personnel_code_validator = RegexValidator(regex='^ST[0-9]{3}$', message="The personnel code should have a format like 'ST001'")
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=10, unique=True, null=True, validators=[
        MaxLengthValidator(10, message='The personnel code must be less than 10 characters'),
    ])

    # all additional fields on the AbstractUser are required to be optional. Enforce mandatoriness at the code level
    designation = models.CharField(max_length=20, choices=PERSONNEL_DESIGNATION_CHOICES, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=PERSONNEL_GENDER_CHOICES, null=True, blank=True)
    tel = models.CharField(max_length=14, unique=True, validators=[PHONE_REGEX], null=True, blank=True)


class WhatsAppGroup(TimeModel):
    group_name = models.CharField(max_length=150, unique=True, null=False, blank=False)
    datetime_created = models.DateTimeField(auto_now_add=False, null=False, blank=False)
    created_by = models.CharField(max_length=100, unique=False, null=False, blank=False)


class WhatsAppChatFile(TimeModel):
    group = models.ForeignKey(WhatsAppGroup, on_delete=models.PROTECT, null=True, blank=True)
    google_id = models.CharField(max_length=100, unique=True, null=False, blank=False)
    web_content_link = models.CharField(max_length=180, unique=True, null=False, blank=False)
    # the max size for a char field with an index storing unicode is 191
    title = models.CharField(max_length=150, unique=False, null=False, blank=False)
    datetime_created = models.DateTimeField(auto_now_add=False, null=False, blank=False)
    filesize = models.IntegerField(null=False, blank=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True)
    comments = models.CharField(max_length=2000, null=True, blank=True)


class GroupDailyStats(TimeModel):
    group = models.ForeignKey(WhatsAppGroup, on_delete=models.PROTECT, null=False, blank=False)
    chat_file = models.ForeignKey(WhatsAppChatFile, on_delete=models.PROTECT, null=False, blank=False)
    stats_date = models.DateField(null=False, blank=False)
    new_users = models.SmallIntegerField(null=False, blank=False)
    left_users = models.SmallIntegerField(null=False, blank=False)
    most_active_hr = models.SmallIntegerField(null=False, blank=False, default=-1)
    emojis = models.CharField(max_length=10000, null=True, blank=True)
    no_messages = models.SmallIntegerField(null=False, blank=False)
    no_images = models.SmallIntegerField(null=False, blank=False)
    no_links = models.SmallIntegerField(null=False, blank=False)

    class Meta:
        unique_together = ('group', 'stats_date')


class GroupNameChanges(TimeModel):
    group = models.ForeignKey(WhatsAppGroup, on_delete=models.PROTECT, null=False, blank=False)
    change_datetime = models.DateTimeField(null=False, blank=False)
    from_name = models.CharField(max_length=150, null=False, blank=False)
    to_name = models.CharField(max_length=150, null=False, blank=False)


class UserDailyStats(TimeModel):
    name_phone = models.CharField(max_length=100, null=False, blank=False)
    group = models.ForeignKey(WhatsAppGroup, on_delete=models.PROTECT, null=False, blank=False)
    chat_file = models.ForeignKey(WhatsAppChatFile, on_delete=models.PROTECT, null=False, blank=False)
    stats_date = models.DateField(null=False, blank=False)
    most_active_hr = models.SmallIntegerField(null=False, blank=False, default=-1)
    emojis = models.CharField(max_length=10000, null=True, blank=True)
    no_messages = models.SmallIntegerField(null=False, blank=False)
    no_images = models.SmallIntegerField(null=False, blank=False)
    no_links = models.SmallIntegerField(null=False, blank=False)

    class Meta:
        unique_together = ('name_phone', 'group', 'stats_date')


class MessageLog(TimeModel):
    chat_file = models.ForeignKey(WhatsAppChatFile, on_delete=models.PROTECT, null=False, blank=False, related_name='r_chat_file')
    user = models.ForeignKey(UserDailyStats, on_delete=models.PROTECT, null=False, blank=False, related_name='r_user')
    datetime_sent = models.DateTimeField(auto_now_add=False, null=False, blank=False)
    message = models.CharField(max_length=10000, null=False, blank=False)


"""
    This model allows for the assignment of Business Counselors to Business Advisors
"""
class CounselorAdvisorAssignment(models.Model):
    class Meta:
        unique_together = (('counselor', 'advisor'),)

    counselor = models.ForeignKey(Personnel, on_delete=models.PROTECT, null=False, blank=False, related_name='r_counselor_advisor')
    advisor = models.ForeignKey(Personnel, on_delete=models.PROTECT, null=False, blank=False, related_name='r_advisor_counselor')

"""
    This model allows for the assignment of Business Advisors to Program Managers
"""
class AdvisorManagerAssignment(models.Model):
    class Meta:
        unique_together = (('manager', 'advisor'),)
    
    advisor = models.ForeignKey(Personnel, on_delete=models.PROTECT, null=False, blank=False, related_name='r_advisor_manage')
    manager = models.ForeignKey(Personnel, on_delete=models.PROTECT, null=False, blank=False, related_name='r_manager_advisor')


class CounselorGroupAssignment(models.Model):
    class Meta:
        unique_together = (('counselor', 'group'),)

    counselor = models.ForeignKey(Personnel, on_delete=models.PROTECT, null=False, blank=False, related_name='r_counselor_group')
    group = models.ForeignKey(WhatsAppGroup, on_delete=models.PROTECT, null=False, blank=False, related_name='r_group_counselor')
