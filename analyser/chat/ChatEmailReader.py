import email
import imaplib
import os
import time
import webbrowser
from email.header import decode_header

from analyser.analyser import Analyser
from analyser.chat.UploadFile import UploadFile
from analyser.nlp.WordCloud import WordCloud
from analyser.chat.HtmlToPdf import HtmlToPdf

analyser = Analyser()
uploadFile = UploadFile()

class ChatEmailReader:
    def __init__(self):
        self.username = "tns.sambou@gmail.com"
        self.password = "bptxjihwdukqknws"
    
    
    def readEmail(self):
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        # authenticate
        imap.login(self.username, self.password)
        
        # Select folder to read messages from
        status, messages = imap.select("INBOX")

        # Get all unread messages
        result, data = imap.search(None, "UNSEEN")

        # data returned is in bytes hence we have to convert it to string
        message_ids = (str(data[0], 'UTF8'))
        message_ids = message_ids.split()
        
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
                    print("From:", From)
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
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                # print text/plain emails and skip attachments
                                print(body)
                            elif "attachment" in content_disposition:
                                # download attachment
                                filename = part.get_filename()
                                if filename:
                                    # folder_name = clean(subject)

                                    # Download file
                                    folder_name = 'tmpfiles'

                                    if not os.path.isdir(folder_name):
                                        # make a folder for this email (named after the subject)
                                        os.mkdir(folder_name)
                                    filepath = os.path.join(folder_name, filename)

                                    # download attachment and save it
                                    open(filepath, "wb").write(part.get_payload(decode=True))

                                    # Upload new chat to google drive
                                    uploadFile.upload(filename)

                                    # Delete file from tmpfiles
                                    os.remove("tmpfiles/"+filename)

                                    # Process uploaded files
                                    analyser.process_uploaded_files()

                                    # Process pending chats
                                    analyser.process_pending_chats()
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

    
    def initiateInfiniteLoop(self):
        while True:
            self.readEmail()

    
    def getPDF(self):
        analyser = Analyser()
        wordCloud = WordCloud()

        params = {}
        params['stats'] = analyser.fetch_group_meta(6, None)
        params['name_changes'] = params['stats']['name_changes']
        params['stats'].pop('name_changes')
        params['group_id'] = 6
        params['wordCloud'] = wordCloud.getGroupChat(6)

        pdf = HtmlToPdf.generatePDF("pdf_templates/group_stats.html", params)

    # def printPDF(self):
    #     analyser = Analyser()
    #     wordCloud = WordCloud()
    #     params = {}
    #     params['stats'] = analyser.fetch_group_meta(6, None)
    #     params['name_changes'] = params['stats']['name_changes']
    #     params['stats'].pop('name_changes')
    #     params['group_id'] = 6
    #     params['wordCloud'] = wordCloud.getGroupChat(6)
    #     HtmlToPdf.pdfKit(params)
