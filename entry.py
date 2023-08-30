# This is a testing file for tanalys

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyser.settings.development")
django.setup()

from analyser.models import WhatsAppChatFile


# This file is used
# For Debugging on Dev version
from analyser.cronjobs import ReadEmails
from analyser.chat.Chart import Chart
from analyser.analyser import Analyser
from analyser.chat.Utilities import Utilities
import traceback

old_file_name = '=?UTF-8?Q?WhatsApp_Chat_with_Formac=CC=A7a=CC=83oOHOLO=5FC2=5FErica=2Etxt?='
file_name = Utilities.clean_file_name(old_file_name)
print("BEFORE\n")
print(old_file_name)
print("GOT THIS\n")
print(file_name)
print("AGAIN THIS\n")
print(Utilities.clean_file_name(file_name))
# ReadEmails.processEmail()

# analyser = Analyser()

# 
# file_name  = "WhatsApp Chat with FormaçãoOHOLO -C2-Miriam_FILE.txt"
# fh = analyser.__read_file_with_auto_encoding__('tmpfiles/%s' % file_name)
# first_line = fh.readline().strip()
# second_line = fh.readline().strip()
# print(first_line)
# print(second_line)
# print(fh)
# whatsap_file_id = 498
# item = WhatsAppChatFile.objects.values("id", "google_id", "title", "group_id").get(
#     id=whatsap_file_id
# )

"""
Process all pending chats
"""
# analyser.process_pending_chats()

"""
Process a certain pending chat
"""
# try:
#     item_temp = WhatsAppChatFile.objects.get(pk=whatsap_file_id)
#     item_temp.status = 'pending'
#     item_temp.save()
#     analyser.process_chat(item, "%m/%d")
# except ValueError as e:
#     if str(e) == "Possible Wrong Date Format":
#         analyser.process_chat(item, "%d/%m")
#     else:
#         print(f"Error processing chat as else {item}")
#         traceback.print_exc()
# except Exception:
#     # TODO: Changed this
#     print(f"Error processing chat here {item}")
#     traceback.print_exc()

# 
# Chart.wordCloud(whatsap_file_id)
# # Chart.activeDaysChart(whatsap_file_id)

# def debugDates(group_id):

#     params = {}
#     params["stats"] = analyser.fetch_group_meta(group_id, None)

#     activeDaysChart = {
#         "dates": params["stats"]["active_dates"]["dates"],
#         "messages": params["stats"]["active_dates"]["messages"],
#     }

#     Chart.activeDaysChart(activeDaysChart)

# group_id = 15
# debugDates(group_id)

# Chart.emotionsGraph(group_id)
# Chart.sentimentGraph(group_id)