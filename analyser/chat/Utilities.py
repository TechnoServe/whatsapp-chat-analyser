import sentry_sdk
from datetime import datetime
from tzlocal import get_localzone
import regex as re


from analyser.chat.constants import *
from django.conf import settings
from analyser.common_tasks import Notification, Terminal

import emoji
import json
import pandas as pd
import email.header
import unicodedata

terminal = Terminal()
sentry_sdk.init(settings.SENTRY_DSN)


class Utilities:
    def clean_file_name(filename: str) -> str:
        """
         A FIX fior below issue on latino emails:
        * =?UTF-8?Q?WhatsApp_Chat_with_Formac=CC=A7a=CC=83oOHOLO=5FC2=5FErica=2Etxt?=
        * Should be WhatsApp Chat with FormaçãoOHOLO -C2-Miriam (4).txt

        """
        decoded_parts = email.header.decode_header(filename)
        decoded_filename = ""

        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                if charset:
                    decoded_filename += part.decode(charset)
                else:
                    decoded_filename += part.decode("utf-8", errors="replace")
            else:
                decoded_filename += part
        return unicodedata.normalize("NFKD", decoded_filename)

    def extract_date_from_message(message, date_format):
        try:
            if (
                len(
                    re.findall(
                        "^\d{1,2}\/\d{1,2}\/\d{2}, \d{1,2}:\d{1,2}\s[ap]m",
                        message,
                        re.IGNORECASE | re.UNICODE,
                    )
                )
                != 0
            ):
                date_part = re.findall(
                    "^(\d{1,2}\/\d{1,2}\/\d{2}, \d{1,2}:\d{1,2}\s[ap]m)",
                    message,
                    re.IGNORECASE | re.UNICODE,
                )[0]
                mssg_date = datetime.strptime(date_part, date_format + "/%y, %I:%M %p")

            elif (
                len(
                    re.findall(
                        "^\d{1,2}\/\d{1,2}\/\d{4}, \d{1,2}:\d{1,2}\s[ap]m",
                        message,
                        re.IGNORECASE | re.UNICODE,
                    )
                )
                != 0
            ):
                date_part = re.findall(
                    "^(\d{1,2}\/\d{1,2}\/\d{4}, \d{1,2}:\d{1,2}\s[ap]m)",
                    message,
                    re.IGNORECASE | re.UNICODE,
                )[0]
                mssg_date = datetime.strptime(date_part, date_format + "/%Y, %I:%M %p")

            elif (
                len(
                    re.findall(
                        "^\d{1,2}\/\d{1,2}\/\d{2}, \d{2}:\d{2}",
                        message,
                        re.IGNORECASE | re.UNICODE,
                    )
                )
                != 0
            ):
                date_part = re.findall(
                    "^(\d{1,2}\/\d{1,2}\/\d{2}, \d{2}:\d{2})",
                    message,
                    re.IGNORECASE | re.UNICODE,
                )[0]
                mssg_date = datetime.strptime(date_part, date_format + "/%y, %H:%M")

            elif (
                len(
                    re.findall(
                        "^\d{1,2}\/\d{1,2}\/\d{4}, \d{2}:\d{2}",
                        message,
                        re.IGNORECASE | re.UNICODE,
                    )
                )
                != 0
            ):
                date_part = re.findall(
                    "^(\d{1,2}\/\d{1,2}\/\d{4}, \d{2}:\d{2})",
                    message,
                    re.IGNORECASE | re.UNICODE,
                )[0]
                mssg_date = datetime.strptime(date_part, date_format + "/%Y, %H:%M")

            else:
                # TODO
                print("I can't extract the datetime ")
                raise Exception(
                    "I can't extract the datetime from '%s' - %s" % (message, date_part)
                )

            return mssg_date

        except ValueError:
            if settings.DEBUG:
                terminal.tprint(
                    "I think I am using the wrong date format %s for %s date from %s. I will try the other one."
                    % (date_format, date_part, message),
                    "warn",
                )
            raise ValueError("Possible Wrong Date Format")

    def determine_dateranges(date_range, first_date, last_date):
        # fetch the group metadata

        if date_range is None or date_range == "":
            s_date = first_date
            e_date = last_date

        else:
            dates_ = date_range.split(" - ")
            s_date = datetime.strptime(dates_[0], "%d/%m/%Y")
            e_date = datetime.strptime(dates_[1], "%d/%m/%Y")

        return {
            "empty_db": 0,
            "s_date": s_date.strftime("%d/%m/%Y"),
            "e_date": e_date.strftime("%d/%m/%Y"),
            "ss_date": s_date.strftime("%Y-%m-%d"),
            "ee_date": e_date.strftime("%Y-%m-%d"),
            "max_date": last_date.strftime("%d/%m/%Y"),
            "min_date": first_date.strftime("%d/%m/%Y"),
        }

    def emoji_count(emojis):
        al_emojis = {}
        for c in emojis:
            if c not in al_emojis:
                al_emojis[c] = 0
            al_emojis[c] += 1

        return al_emojis

    def emoji_list(text):
        y = "".join(c for c in text if c in emoji.UNICODE_EMOJI["en"])
        # if y != '': print(y)
        return y

        # emoji_list = []
        # data = re.findall(r'\X', text)
        # for word in data:
        #     if any(char in emoji.UNICODE_EMOJI for char in word):
        #         emoji_list.append(word)
        # return emoji_list

    def process_dated_non_message(chat_mssg):
        reformatted = None
        user_added = re.findall(user_add_regex, chat_mssg, re.IGNORECASE | re.UNICODE)
        user_lefted = re.findall(user_left_regex, chat_mssg, re.IGNORECASE | re.UNICODE)
        user_removed = re.findall(
            removed_users_regex, chat_mssg, re.IGNORECASE | re.UNICODE
        )

        if len(user_added) == 1 and len(user_added[0]) == 2 and user_added[0][1] != "":
            # mimick a message
            dummy = user_added[0]
            reformatted = (dummy[0], dummy[1], chat_mssg)

        elif len(user_lefted) == 1 and len(user_lefted[0]) == 3:
            # mimick a message
            # print("%s LEFT" % user_lefted[0][1])
            dummy = user_lefted[0]
            reformatted = (dummy[0], dummy[1], chat_mssg)

        elif len(user_removed) == 1:
            # mimick a message
            dummy = user_removed[0]
            reformatted = (dummy[0], dummy[1], chat_mssg)

        elif len(
            re.findall(send_mssg_settings_regex, chat_mssg, re.IGNORECASE | re.UNICODE)
        ):
            return -1
        elif len(re.findall(grp_icon_regex, chat_mssg, re.IGNORECASE | re.UNICODE)):
            return -1
        elif len(
            re.findall(
                security_code_change_regex, chat_mssg, re.IGNORECASE | re.UNICODE
            )
        ):
            return -1
        elif len(
            re.findall(number_change_regex, chat_mssg, re.IGNORECASE | re.UNICODE)
        ):
            return -1

        else:
            if settings.DEBUG:
                terminal.tprint(
                    "I don't know how to process the message: '%s'" % chat_mssg, "warn"
                )
            # if len(re.findall('added', chat_mssg, re.IGNORECASE | re.UNICODE)) != 0:
            # print(chat_mssg.strip())
            # print(user_added)

        return reformatted
