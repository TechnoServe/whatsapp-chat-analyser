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
import traceback

# ReadEmails.processEmail()

analyser = Analyser()

whatsap_file_id = 462
item = WhatsAppChatFile.objects.values("id", "google_id", "title", "group_id").get(
    id=whatsap_file_id
)

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


Chart.wordCloud(whatsap_file_id)
