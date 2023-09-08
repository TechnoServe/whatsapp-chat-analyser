# This is a testing file
# Didn't have enough time to setup testing e.t.c, will do that later,
# I run it with
########   nodemon --exec pipenv run python entry.py   #######
# nodemon to detect any changes and speed up testing

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyser.settings.development")
django.setup()

from analyser.models import WhatsAppChatFile

import regex as re

# This file is used
# For Debugging on Dev version
from analyser.cronjobs import ReadEmails
from analyser.chat.Chart import Chart
from analyser.analyser import Analyser
from analyser.chat.Utilities import Utilities
import traceback
from analyser.chat.constants import *

from analyser.chat.ChatEmailReader import ChatEmailReader

email_reader = ChatEmailReader()
show_sentiment = email_reader.__is_english__(30)
print(show_sentiment)
show_sentiment = email_reader.__is_english__(541)
print(show_sentiment)

email_reader.__getPDF__(
    30, "WhatsApp Chat with FormaçãoOHOLO_C2_Erica.txt", 541, "nehemie054@gmail.com"
)
