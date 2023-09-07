import os
import os.path
from oauth2client import file
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from analyser.models import (
    WhatsAppGroup,
    WhatsAppChatFile,
)
from django.db import transaction
from analyser.chat.Utilities import Utilities


# This app makes use of Google Authentication to authenticate clients
# The file client_secrets.json contains the app developer's OAuth 2 secrets
class UploadFile:
    def upload(self, fileName):
        """ param sender_email"""
        if not os.path.exists("mycreds.txt"):
            gauth = GoogleAuth()
            gauth.LocalWebserverAuth()
            gauth.SaveCredentialsFile("mycreds.txt")

        self.gauth = GoogleAuth()
        self.gauth.LoadCredentialsFile("mycreds.txt")
        self.drive = GoogleDrive(self.gauth)

        folderId = os.environ["GCP_DRIVE_ID"]

        uploadFile = self.drive.CreateFile(
            {"parents": [{"id": folderId}], "title": fileName}
        )
        uploadFile.SetContentFile("tmpfiles/" + fileName)
        uploadFile.Upload()


        #
        # TODO
        # This is where you would be attaching file ids from google to emails which sent them
        #
        # WhatsAppChatFile(
        #     google_id=chat["google_id"],
        #     web_content_link=chat["web_content_link"],
        #     title=Utilities.clean_file_name(chat["title"]),
        #     datetime_created=chat["datetime_created"],
        #     filesize=chat["filesize"],
        #     status=status_,
        #     comments=self.chat_file_comments,
        # ).save()
        # transaction.commit()

        return True
