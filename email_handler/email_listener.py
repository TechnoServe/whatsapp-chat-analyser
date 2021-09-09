'''
script that listens for emails from group admins
downloads attachment
sends back analysis
'''
import email
import imaplib
import os
import random
import smtplib
import ssl
import sys
import traceback
from email import encoders
from email.header import decode_header
# Create a secure SSL context
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import listdir

from mspark_whatsapp_analyzer import settings
from mspark_whatsapp_analyzer.settings import env

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mspark_whatsapp_analyzer.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from mspark_whatsapp_analyzer import settings
from utils.analysis import process_chat_file



context = ssl.create_default_context()


# from uploads.models import ChatUpload


class Mail():
    def __init__(self):
        try:
            self.username = env("EMAIL_SENDER")
            self.password = env("EMAIL_PASSWORD")
            self.imap = imaplib.IMAP4_SSL("imap.gmail.com")
            self.imap.login(self.username, self.password)
            print("logged in to email")
            self.smtp_server = smtplib.SMTP(env("EMAIL_HOST"), env("EMAIL_PORT"))
            self.smtp_server.ehlo()
            self.smtp_server.starttls(context=context)
            self.smtp_server.ehlo()
            self.smtp_server.login(self.username, self.password)
            self.smtp_server.set_debuglevel(1)
            self.receiver_email = ""
            self.message = ""
            self.filename = ""
            self.subject = ""
            self.email_id = ""
            self.chat_file_directory = ""
        except Exception as e:
            print(e)

    def generate_email_ID(self):
        return random.randint(0000, 9999)

    def parse_email(self, mail):
        try:
            res, msg = self.imap.fetch(mail, "(RFC822)")
            for response in msg:
                if isinstance(response, tuple):
                    # parse a bytes email into a message object
                    msg = email.message_from_bytes(response[1])
                    # decode the email subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        # if it's a bytes, decode to str
                        subject = subject.decode(encoding)
                    # decode email sender
                    From, encoding = decode_header(msg.get("From"))[0]
                    if isinstance(From, bytes):
                        From = From.decode(encoding)

                    self.subject, self.receiver_email = subject, From

                    return msg
        except Exception as e:
            traceback.print_exc()
            print(e)

    def construct_message(self, chat_file_path, body):
        try:
            message = MIMEMultipart()
            message["From"] = self.username
            message["To"] = self.receiver_email
            message["Subject"] = "Analysis results for Group {} ".format(self.subject)
            message["Bcc"] = ""
            msg = "Dear {first_name}, WhatsApp Group Export uploaded successfully. Find analysis attached in this email. Incase of any issues, contact {}."
            if chat_file_path is not "":
                process_chat_file(chat_file_path)
                f = listdir(self.chat_file_directory)
                if len(f) > 2:
                    message.attach(MIMEText(msg, "html"))
                    for f in listdir(self.chat_file_directory):
                        if not f.endswith('.txt'):
                            try:
                                file_name = f.split("/")[-1]
                                part = MIMEBase('application', "octet-stream")
                                part.set_payload(open(os.path.join(self.chat_file_directory, f), "rb").read())
                                encoders.encode_base64(part)
                                part.add_header('Content-Disposition', 'attachment', filename=file_name)
                                message.attach(part)
                            except Exception as e:
                                print("could not attach file", e)
                else:
                    print("Files not attached")
                    message.attach(
                        MIMEText("Had trouble analyzing this file. Please send another export file.", "html"))
            # print(message)
            return message
        except Exception as e:
            print(e)


    def check_mail(self):
        print("checking email")
        self.imap.select("INBOX")
        status, self.unRead = self.imap.search(None, 'UnSeen')
        if len(self.unRead[0].split()) > 0:
            for mail in self.unRead[0].split():
                msg = self.parse_email(mail)
                if msg:
                    response_message, chat_file_path = self.extract_mail_body(msg)
                    if response_message:
                        message_body = self.construct_message(chat_file_path, response_message)
                        # print("message_body: ", message_body)
                        if message_body:
                            self.send_email(message_body)
                            # self.save_file_objects(chat_file_path)
        else:
            print("no new email")

    def get_chat_file_directory(self):
        self.email_id = self.generate_email_ID()
        self.chat_file_directory = os.path.join(settings.MEDIA_ROOT, self.subject.replace(" ", ""))
        if not os.path.exists(self.chat_file_directory):
            os.makedirs(self.chat_file_directory)
        return self.chat_file_directory

    def extract_mail_body(self, msg):
        message = ""
        chat_file_path = ""
        if msg and msg.is_multipart():
            # iterate over email parts
            for part in msg.walk():
                # extract content type of email
                content_disposition = str(part.get("Content-Disposition"))
                try:
                    #  attachment available
                    if content_disposition is not None and "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename.endswith(".txt"):
                            # message = ""
                            chat_file_path = os.path.join(self.get_chat_file_directory(), filename)
                            with open(chat_file_path, "wb") as f:
                                f.write(part.get_payload(decode=True))
                                f.close()

                        else:
                            message += " {} could not be processed. ".format(
                                part.get_filename())
                    else:
                        message = "Please send a WhatsApp Export File. "
                except Exception as e:
                    print(e)
        else:
            message = "No file was attached in this email. Please retry with a Whatsapp Export file."

        return message, chat_file_path

    def send_email(self, msg):
        try:
            self.smtp_server.sendmail(env('EMAIL_SENDER'), self.receiver_email, msg.as_string())
        except Exception as e:
            print(e)
