from django.db import transaction, connection
from django.db.models import Q, Sum, Count, IntegerField, Min, Max, Avg, F, CharField, functions
from django.conf import settings

from analyser.models import Personnel, WhatsAppGroup, WhatsAppChatFile, GroupDailyStats, UserDailyStats, MessageLog, GroupNameChanges, STATUS_CHOICES
from analyser.serializers import GroupDailyStatsSerializer, MessageLogSerializer
from analyser.chat.Utilities import Utilities

from hashids import Hashids
from analyser.common_tasks import Notification, Terminal

import pandas as pd
import sentry_sdk

from datetime import datetime
from tzlocal import get_localzone

class MessageHistory:

    def getMessageLogByDate(self, date, group_id):
        #all_messages = list(MessageLog.objects.select_related('user').filter(datetime_sent=date, chat_file_id=group_id).extra(select={'dt':"DATE_FORMAT(datetime_sent, '%%Y-%%m-%%d %%H:%%i')"}).values('dt').annotate(mssg=F('message')).order_by('datetime_sent').all())
        qs = MessageLog.objects.select_related('user').filter(datetime_sent__date=date, chat_file=group_id).extra(select={'dt':"DATE_FORMAT(datetime_sent, '%%Y-%%m-%%d %%H:%%i')"}).all()

        result = MessageLogSerializer(qs, many=True)
        return result.data