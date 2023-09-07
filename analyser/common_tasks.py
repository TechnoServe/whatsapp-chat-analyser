import smtplib
import os
import re
import sentry_sdk

from django.conf import settings

# import django-rq if we are using queues
try:
    import django_rq
except Exception:
    pass

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Template, FileSystemLoader
from jinja2.environment import Environment

sentry_sdk.init(settings.SENTRY_DSN)


class Emails:
    def __init__(self):
        terminal.tprint("Initializing the Email class", "ok")

    def send_email(to, sender, cc, subject=None, body=None, add_to_queue=False):
        """sends email using a Jinja HTML template"""
        # convert TO into list if string
        if type(to) is not list:
            to = to.split()

        to_list = to
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SITE_NAME
        msg["Subject"] = subject
        msg["To"] = ",".join(to)
        if cc is not None:
            msg["Cc"] = ",".join(cc)
            to_list = to_list + cc

        to_list = [_f for _f in to_list if _f]  # remove null emails

        msg.attach(MIMEText("Alternative text", "plain"))
        msg.attach(MIMEText(body, "html"))
        try:
            terminal.tprint("setting up the SMTP con....", "debug")
            if add_to_queue == True:
                django_rq.enqueue(queue_email, to_list, msg)
            else:
                server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
                server.starttls()
                server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
                server.sendmail(settings.SITE_NAME, to_list, msg.as_string())
                server.quit()
        except Exception as e:
            terminal.tprint("Error sending email -- %s" % str(e), "error")
            raise Exception("Error sending email -- %s" % str(e))


class Notification:
    def send_email(self, email_settings):
        try:
            self.env = Environment()
            self.env.loader = FileSystemLoader(settings.TEMPLATES[0]["DIRS"][0])

            template = self.env.get_template(email_settings["template"])
            email_settings["site_name"] = settings.SITE_NAME
            email_html = template.render(email_settings)
            cc = email_settings["cc"] if "cc" in email_settings else None
            use_queue = (
                email_settings["use_queue"] if "use_queue" in email_settings else False
            )

            Emails.send_email(
                email_settings["recipient_email"],
                email_settings["sender_email"],
                cc,
                email_settings["subject"],
                email_html,
                use_queue,
            )
        except Exception as e:
            if settings.DEBUG:
                terminal.tprint(str(e), "fail")
            sentry_sdk.capture_exception(e)
            raise Exception(str(e))

    def send_sentry_message(
        self,
        message="Test message",
        err_level="info",
        extra_data=None,
        tags=None,
        user_data=None,
    ):
        with sentry_sdk.push_scope() as scope:
            if tags:
                for tag in tags:
                    scope.set_tag(tag["tag"], tag["value"])

            if user_data:
                for u in user_data:
                    scope.user = {u["tag"]: u["value"]}

            if extra_data:
                for ed in extra_data:
                    scope.set_extra(ed["tag"], ed["value"])

            sentry_sdk.capture_message(message, err_level)


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Terminal:
    def __init__(self):
        self.HEADER = "\033[95m"
        self.OKBLUE = "\033[94m"
        self.OKGREEN = "\033[92m"
        self.WARNING = "\033[93m"
        self.FAIL = "\033[91m"
        self.ENDC = "\033[0m"
        self.BOLD = "\033[1m"
        self.UNDERLINE = "\033[4m"

    def tprint(self, message, msg_type):
        if msg_type == "warn":
            tcolor = bcolors.WARNING
        elif msg_type == "ok":
            tcolor = bcolors.OKGREEN
        elif msg_type == "okblue":
            tcolor = bcolors.OKBLUE
        elif msg_type == "underline":
            tcolor = bcolors.UNDERLINE
        elif msg_type == "fail":
            tcolor = bcolors.FAIL
        elif msg_type == "header":
            tcolor = bcolors.HEADER
        elif msg_type == "info":
            tcolor = bcolors.OKBLUE
        elif msg_type == "debug":
            tcolor = bcolors.WARNING
        elif msg_type == "error":
            tcolor = bcolors.FAIL

        print((tcolor + message + bcolors.ENDC))


def validate_phone_number(phone_no):
    # given any phone number, validates it and returns a valid number else returns None
    phone_number = re.findall(
        "^\(?(?:\+?254|0)((?:7|1)\)?(?:[ -]?[0-9]){2}\)?(?:[ -]?[0-9]){6})$", phone_no
    )
    if len(phone_number) == 0:
        return None
    else:
        return "+254%s" % phone_number[0]


terminal = Terminal()
