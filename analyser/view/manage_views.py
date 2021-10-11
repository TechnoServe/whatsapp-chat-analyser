import os
import re
import json
import sentry_sdk

from io import StringIO as IO

from django.db.models import Count
from django.db.utils import DataError
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.http.response import HttpResponseRedirect
from django.middleware import csrf
from django_registration.exceptions import ActivationError
from django_registration.backends.activation.views import RegistrationView, ActivationView
from django.shortcuts import render, redirect
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import resolve, reverse
from hashids import Hashids

from jinja2 import Template

from analyser.models import Personnel, WhatsAppGroup, WhatsAppChatFile, UserDailyStats, PERSONNEL_DESIGNATION_CHOICES
from analyser.common_tasks import Notification, Terminal
from analyser.analyser import Analyser
from analyser.serializers import PersonnelSerializer, WhatsAppGroupSerializer, WhatsAppChatFileSerializer, UserDailyStatsSerializer

terminal = Terminal()
sentry_sdk.init(settings.SENTRY_DSN)

cur_user_email = None
my_hashids = Hashids(min_length=5, salt=settings.SECRET_KEY)

User = get_user_model()

