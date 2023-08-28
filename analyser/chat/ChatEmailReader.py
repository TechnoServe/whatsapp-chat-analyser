import email
import imaplib
import os
import time
import webbrowser
from email.header import decode_header
from django.core.mail import EmailMessage

from analyser.analyser import Analyser
from analyser.chat.UploadFile import UploadFile
from analyser.nlp.WordCloud import WordCloud
from analyser.chat.HtmlToPdf import HtmlToPdf

from analyser.models import WhatsAppChatFile
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

from analyser.chat.Chart import Chart
import traceback
from django.core.cache import cache
from django.db import transaction, connection
from django.http import HttpResponse, JsonResponse

analyser = Analyser()
uploadFile = UploadFile()


class ChatEmailReader:
    def __init__(self):
        self.username = os.environ["CHAT_BOT_EMAIL"]
        self.password = os.environ["CHAT_BOT_PASSWORD"]
        self.tmp_subjectname = ""

    def readEmail(self):
        print("STARTED READING EMAILS")
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        # authenticate
        imap.login(self.username, self.password)

        # Select folder to read messages from
        status, messages = imap.select("INBOX")

        # Get all unread messages
        result, data = imap.search(None, "UNSEEN")

        # data returned is in bytes hence we have to convert it to string
        message_ids = str(data[0], "UTF8")
        message_ids = message_ids.split()

        # TODO: Delete this (for testing)
        # message_ids = [399]

        for i in message_ids:
            # fetch the email message by ID
            res, msg = imap.fetch(str(i), "(RFC822)")
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

                    # Extract sender email
                    senderEmail = email.utils.parseaddr(From)[1]

                    print("Sender email = " + senderEmail)
                    print("Subject:", subject)
                    self.tmp_subjectname = subject
                    print("From:", From)

                    # Validate the source of an email address (from tns.org and tnslabs.org only)
                    if not senderEmail.endswith(("tns.org", "tnslabs.org")):
                        print("Sender Email not from TNS")
                        return

                    # if the email message is multipart
                    if msg.is_multipart():
                        # iterate over email parts
                        for part in msg.walk():
                            # extract content type of email
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            try:
                                # get the email body
                                body = part.get_payload(decode=True).decode()
                            except:
                                pass
                            if (
                                content_type == "text/plain"
                                and "attachment" not in content_disposition
                            ):
                                # print text/plain emails and skip attachments
                                print(body)
                            elif "attachment" in content_disposition:
                                # download attachment
                                filename = part.get_filename()
                                if filename:
                                    # folder_name = clean(subject)

                                    # Download file
                                    folder_name = "tmpfiles"

                                    if not os.path.isdir(folder_name):
                                        # make a folder for this email (named after the subject)
                                        os.mkdir(folder_name)
                                    filepath = os.path.join(folder_name, filename)

                                    # download attachment and save it
                                    open(filepath, "wb").write(
                                        part.get_payload(decode=True)
                                    )

                                    # Upload new chat to google drive
                                    uploadFile.upload(filename)

                                    # Delete file from tmpfiles
                                    os.remove("tmpfiles/" + filename)

                                    # Process uploaded files
                                    try:
                                        analyser.process_uploaded_files()
                                    except:
                                        print(
                                            "Met an error while process_uploaded_files files"
                                        )
                                        traceback.print_exc()

                                    # Process pending chats
                                    try:
                                        analyser.process_pending_chats()
                                    except:
                                        print(
                                            "Met an error while process_pending_chats"
                                        )
                                        traceback.print_exc()

                                    # Send report of file name to provided email
                                    self.report_file(
                                        filename=filename, senderEmail=senderEmail
                                    )

                    else:
                        # extract content type of email
                        content_type = msg.get_content_type()
                        # get the email body
                        body = msg.get_payload(decode=True).decode()
                        if content_type == "text/plain":
                            # print only text email parts
                            print(body)
        # close the connection and logout
        imap.close()
        imap.logout()
        time.sleep(1)

    def report_file(self, filename, senderEmail) -> JsonResponse:
        # get uploaded file id
        # TODO (Done) it was getting old uploaded files which some were not processed successfuly, which was causing missing log messages while generating word cloud
        # ISSUE (Fixed) Daily Stats were saved for file 482, while wordcloud was getting, word cloud for 418
        # Based on the latest it was saved (Logic being if were processing a certain unread message, the probability is that it is the last)

        print(f"Reporting Chat file_name {filename}")
        try:
            chat_file = (
                WhatsAppChatFile.objects.filter(title=filename)
                .values_list("group_id", "title", "id")
                .latest("datetime_created")
            )
        except:
            return JsonResponse(
                {
                    "status": "Error analyzing the file",
                    "error": True,
                },
                status=400,
            )
        # TODO (Done)
        # When we are about to send the user the report we save the email for future resending
        # Implemented it this way because there was no easy way to associate a chatfile id with an email
        try:
            file_id = chat_file[2]
            file = WhatsAppChatFile.objects.get(pk=file_id)
            file.email = senderEmail
            file.save()
            transaction.commit()  # Adding this because changes were not being saved

        except Exception as e:
            traceback.print_exc()
            return JsonResponse(
                {
                    "message": "Error analyzing the file",
                    "error": True,
                },
                status=400,
            )

        # Get group ID
        self.__getPDF__(
            group_id=chat_file[0],
            fileName=chat_file[1],
            chat_file_id=chat_file[2],
            to=senderEmail,
        )
        return JsonResponse({"message": "File analyzed successfully"})

    def initiateInfiniteLoop(self):
        while True:
            self.readEmail()

    def __getPDF__(self, group_id, fileName, chat_file_id, to):
        analyser = Analyser()
        wordCloud = WordCloud()

        params = {}
        params["stats"] = analyser.fetch_group_meta(group_id, None)

        params["name_changes"] = params["stats"]["name_changes"]
        params["stats"].pop("name_changes")
        params["group_id"] = group_id

        pdfFile = fileName.replace(".txt", ".pdf")
        params["fileName"] = pdfFile
        params["s_date"] = "2021-09-10"
        params["e_date"] = "2021-10-11"

        chartData = [
            params["stats"]["images_count"],
            params["stats"]["messages_count"],
            params["stats"]["links_count"],
            params["stats"]["emojis_count"],
        ]

        activeDaysChart = {
            "dates": params["stats"]["active_dates"]["dates"],
            "messages": params["stats"]["active_dates"]["messages"],
        }

        Chart.CategoriesOfInformation(chartData)

        Chart.activeDaysChart(activeDaysChart)
        Chart.wordCloud(chat_file_id)

        Chart.emotionsGraph(group_id)
        Chart.sentimentGraph(group_id)

        pdf = HtmlToPdf.generatePDF("pdf_templates/group_stats.html", params)

        self.sendEmail(pdfFile, to)

    def sendEmail(self, pdf_filename, to):
        smtp_ssl_host = "smtp.gmail.com"
        smtp_ssl_port = 465
        sender = self.username
        targets = [
            to,
        ]

        msg = MIMEMultipart()
        txt = MIMEText("Kindly find attached, a copy of the generated report.")

        analysis_for = self.tmp_subjectname if self.tmp_subjectname else pdf_filename

        msg["Subject"] = "Chat Analysis for " + " " + analysis_for
        msg["From"] = sender
        msg["To"] = ", ".join(targets)

        msg.attach(txt)

        filepath = "pdfFiles/" + pdf_filename
        with open(filepath, "rb") as f:
            pdf = MIMEImage(f.read(), _subtype="pdf")

        pdf.add_header(
            "Content-Disposition", "attachment", filename=os.path.basename(filepath)
        )
        msg.attach(pdf)

        server = smtplib.SMTP_SSL(smtp_ssl_host, smtp_ssl_port)
        server.login(self.username, self.password)
        server.sendmail(sender, targets, msg.as_string())
        server.quit()

    def printPDF(self):
        analyser = Analyser()
        wordCloud = WordCloud()
        params = {}
        params["stats"] = analyser.fetch_group_meta(6, None)
        params["name_changes"] = params["stats"]["name_changes"]
        params["stats"].pop("name_changes")
        params["group_id"] = 6
        params["wordCloud"] = wordCloud.getGroupChat(6)
        HtmlToPdf.pdfKit(params)

    def weasyPrint(self):
        analyser = Analyser()
        wordCloud = WordCloud()
        params = {}

        params["s_date"] = "2021-10-09"
        params["e_date"] = "2021-09-09"
        params["page_title"] = "Group Statistics"
        params["request"] = {}

        params["stats"] = analyser.fetch_group_meta(6, None)
        params["name_changes"] = params["stats"]["name_changes"]
        params["stats"].pop("name_changes")
        params["group_id"] = 6
        params["wordCloud"] = wordCloud.getGroupChat(6)
        params["graph"] = self.return_graph()

        chartData = [
            params["stats"]["images_count"],
            params["stats"]["messages_count"],
            params["stats"]["links_count"],
            params["stats"]["emojis_count"],
        ]

        activeDaysChart = {
            "dates": params["stats"]["active_dates"]["dates"],
            "messages": params["stats"]["active_dates"]["messages"],
        }

        Chart.CategoriesOfInformation(chartData)

        Chart.activeDaysChart(activeDaysChart)
        Chart.emotionsGraph(params["group_id"])
        Chart.sentimentGraph(params["group_id"])

        HtmlToPdf.generatePDF(params)

    def return_graph(self):
        import matplotlib.pyplot as plt
        from io import StringIO
        import numpy as np

        x = np.arange(0, np.pi * 3, 0.1)
        y = np.sin(x)

        fig = plt.figure()
        plt.plot(x, y)

        plt.savefig("analyser/templates/jinja2/pdf_templates/pie_chart.png")

        imgdata = StringIO()
        fig.savefig(imgdata, format="svg")
        imgdata.seek(0)

        data = imgdata.getvalue()
        return data
