from datetime import datetime
from tzlocal import get_localzone

class Utilities:
    def extract_date_from_message(message, date_format):
        try:
            if len(re.findall('^\d{1,2}\/\d{1,2}\/\d{2}, \d{1,2}:\d{1,2}\s[ap]m', message, re.IGNORECASE)) != 0:
                date_part = re.findall('^(\d{1,2}\/\d{1,2}\/\d{2}, \d{1,2}:\d{1,2}\s[ap]m)', message, re.IGNORECASE)[0]
                mssg_date = datetime.strptime(date_part, date_format + '/%y, %I:%M %p')
            
            elif len(re.findall('^\d{1,2}\/\d{1,2}\/\d{4}, \d{1,2}:\d{1,2}\s[ap]m', message, re.IGNORECASE)) != 0:
                date_part = re.findall('^(\d{1,2}\/\d{1,2}\/\d{4}, \d{1,2}:\d{1,2}\s[ap]m)', message, re.IGNORECASE)[0]
                mssg_date = datetime.strptime(date_part, date_format + '/%Y, %I:%M %p')
            
            elif len(re.findall('^\d{1,2}\/\d{1,2}\/\d{2}, \d{2}:\d{2}', message, re.IGNORECASE)) != 0:
                date_part = re.findall('^(\d{1,2}\/\d{1,2}\/\d{2}, \d{2}:\d{2})', message, re.IGNORECASE)[0]
                mssg_date = datetime.strptime(date_part, date_format + '/%y, %H:%M')
            
            elif len(re.findall('^\d{1,2}\/\d{1,2}\/\d{4}, \d{2}:\d{2}', message, re.IGNORECASE)) != 0:
                date_part = re.findall('^(\d{1,2}\/\d{1,2}\/\d{4}, \d{2}:\d{2})', message, re.IGNORECASE)[0]
                mssg_date = datetime.strptime(date_part, date_format + '/%Y, %H:%M')
        
            else:
                raise Exception("I can't extract the datetime from '%s' - %s" % (message, date_part))

            return mssg_date

        except ValueError:
            if settings.DEBUG: terminal.tprint("I think I am using the wrong date format %s for %s date from %s. I will try the other one." % (date_format, date_part, message), 'warn')
            raise ValueError("Possible Wrong Date Format")


    def determine_dateranges(date_range, first_date, last_date):
        # fetch the group metadata
        if date_range is None:
            s_date = first_date
            e_date = last_date

        else:
            dates_ = date_range.split(' - ')
            s_date = datetime.strptime(dates_[0], '%d/%m/%Y')
            e_date = datetime.strptime(dates_[1], '%d/%m/%Y')

        return {
            'empty_db': 0,
            's_date': s_date.strftime('%d/%m/%Y'),
            'e_date': e_date.strftime('%d/%m/%Y'),
            'ss_date': s_date.strftime('%Y-%m-%d'),
            'ee_date': e_date.strftime('%Y-%m-%d'),
            'max_date': last_date.strftime('%d/%m/%Y'),
            'min_date': first_date.strftime('%d/%m/%Y')
        }
    
    def emoji_count(emojis):
        al_emojis = {}
        for c in emojis:
            if c not in al_emojis: al_emojis[c] = 0
            al_emojis[c] += 1

        return al_emojis
    

    def emoji_list(text):
        y = ''.join(c for c in text if c in emoji.UNICODE_EMOJI['en'])
        # if y != '': print(y)
        return y

        emoji_list = []
        data = re.findall(r'\X', text)
        for word in data:
            if any(char in emoji.UNICODE_EMOJI for char in word):
                emoji_list.append(word)
        return emoji_list
    

    def process_dated_non_message(chat_mssg):
        reformatted = None
        user_added = re.findall(user_add_regex, chat_mssg, re.IGNORECASE)
        user_lefted = re.findall(user_left_regex, chat_mssg, re.IGNORECASE)
        user_removed = re.findall(removed_users_regex, chat_mssg, re.IGNORECASE)

        if len(user_added) == 1 and len(user_added[0]) == 2 and user_added[0][1] != '':
            #mimick a message
            dummy = user_added[0]
            reformatted = (dummy[0], dummy[1], chat_mssg)
        
        elif len(user_lefted) == 1 and len(user_lefted[0]) == 3:
            #mimick a message
            # print("%s LEFT" % user_lefted[0][1])
            dummy = user_lefted[0]
            reformatted = (dummy[0], dummy[1], chat_mssg)

        elif len(user_removed) == 1:
            #mimick a message
            dummy = user_removed[0]
            reformatted = (dummy[0], dummy[1], chat_mssg)

        elif len(re.findall(send_mssg_settings_regex, chat_mssg, re.IGNORECASE)): return -1
        elif len(re.findall(grp_icon_regex, chat_mssg, re.IGNORECASE)): return -1
        elif len(re.findall(security_code_change_regex, chat_mssg, re.IGNORECASE)): return -1
        elif len(re.findall(number_change_regex, chat_mssg, re.IGNORECASE)): return -1

        else:
            if settings.DEBUG: terminal.tprint("I don't know how to process the message: '%s'" % chat_mssg, 'warn')
            # if len(re.findall('added', chat_mssg, re.IGNORECASE)) != 0:
            # print(chat_mssg.strip())
            # print(user_added)

        return reformatted