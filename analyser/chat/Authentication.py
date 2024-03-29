import os.path
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# This app makes use of Google Authentication to authenticate clients
# The file client_secrets.json contains the app developer's OAuth 2 secrets
class Authenticator: 
    def authenticate(self):
        if not os.path.exists("mycreds.txt"):
            gauth = GoogleAuth()
            gauth.LocalWebserverAuth()
            gauth.SaveCredentialsFile("mycreds.txt")

        self.gauth = GoogleAuth()
        self.gauth.LoadCredentialsFile("mycreds.txt") 
        self.drive = GoogleDrive(self.gauth)