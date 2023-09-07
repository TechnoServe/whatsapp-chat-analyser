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


def try_analyse():
    analyser = Analyser()
    try:
        analyser.process_uploaded_files()
    except:
        print("Met an error while uploading files")
        traceback.print_exc()

    # Process pending chats
    try:
        analyser.process_pending_chats()
    except:
        print("Met an error while processing pending charts")
        traceback.print_exc()


try_analyse()
# old_file_name = (
#     "=?UTF-8?Q?WhatsApp_Chat_with_Formac=CC=A7a=CC=83oOHOLO=5FC2=5FErica=2Etxt?="
# )
# file_name = Utilities.clean_file_name(old_file_name)
# print("BEFORE\n")
# print(old_file_name)
# print("GOT THIS\n")
# print(file_name)
# print("AGAIN THIS\n")
# print(Utilities.clean_file_name(file_name))

# with open(
#     "tmpfiles/WhatsApp Chat with FormaçãoOHOLO_C2_Erica.txt", "r", encoding="utf-8"
# ) as file:
#     print(file.readline())

# # with open(file_name, "w") as p:
# #     p.write("Sample mannnn")
# # ReadEmails.processEmail()

# analyser = Analyser()

# #
# file_name = "WhatsApp Chat with FormaçãoOHOLO_C2_Erica.txt"
# group_name = analyser.extract_group_name_from_filename(file_name)
# print(f"GROUP NAME {group_name}")


# Testing group attributes function
# file_name = "WhatsApp Chat with FormaçãoOHOLO -C2-Miriam (1).txt"
# print(
#     '1/30/23, 09:25 - Érica Muarramuassa created group "Treinamento OHOLO"'.encode(
#         "utf-8"
#     ).decode("ASCII")
# )
file = analyser.__read_file_with_auto_encoding__("tmpfiles/%s" % file_name)
grp_attr = analyser.__get_group_attr__(file)
print(grp_attr)

print("MESSAGE ANALYSE with UNICODE")
lines = [
    "5/31/23, 07:17 - Érica Muarramuassa: IMG-20230531-WA0010.jpg (file attached)",
    "6/4/23, 13:35 - Érica Muarramuassa: Yu😍😍😍",
    "6/17/23, 13:48 - Eleutéria Acides: Assim tugo que aprederam durante 4 meses não foi útil 😞",
    "6/18/23, 19:11 - Érica Muarramuassa: Carlota Bene 2023.vcf (file attached)",
    "1/30/23, 12:01 - Érica Muarramuassa: Bom dia Mana Eleuteria. Bem vinda a nossa turma das Manas do OHOLO",
    '2/2/23, 16:14 - Érica Muarramuassa changed the group name from "Treinamento OHOLO" to "FormaçãoOHOLO_C2_Erica"',
    "2/2/23, 16:55 - Érica Muarramuassa added +258 84 377 7302",
    "2/2/23, 16:57 - Érica Muarramuassa: Boa tarde minhas manas como estão?",
]
for line in lines:
    msg = analyser.process_dated_non_message(line)
    anals = analyser.process_chat_message(line)
    print(anals)
    msg = re.findall(msg_line_regex, line, re.IGNORECASE | re.UNICODE)
    print(msg)
# for line in fh:
#     try:
#         cur_date = analyser.extract_date_from_message(line, "%d/%m")
#     except ValueError as e:
#         if str(e) == "Possible Wrong Date Format":
#             cur_date = analyser.extract_date_from_message(line, "%m/%d")
#         else:
#             print("It is a different kind of error 💀💀")
#     except Exception:
#         print("Error reformatting the date 💀💀")
#     print(cur_date)

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
