import re
import sentry_sdk
import os.path
import emoji
import json
import pandas as pd

from django.db import transaction, connection
from django.db.models import Q, Sum, Count, IntegerField, Min, Max, Avg, F, CharField, functions
from django.conf import settings
# from pydrive.auth import GoogleAuth
# from pydrive.drive import GoogleDrive
from hashids import Hashids
from datetime import datetime
from tzlocal import get_localzone

from .models import Personnel, WhatsAppGroup, WhatsAppChatFile, GroupDailyStats, UserDailyStats, MessageLog, GroupNameChanges, STATUS_CHOICES
from analyser.serializers import GroupDailyStatsSerializer
from .common_tasks import Notification, Terminal

# Import regex constants
from analyser.chat.constants import *

# Import Authenticator Service
from analyser.chat.Authentication import Authenticator


terminal = Terminal()
sentry_sdk.init(settings.SENTRY_DSN)
my_hashids = Hashids(min_length=5, salt=settings.SECRET_KEY)


SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# You changed the subject from "mSPARK MSA DUKAS T1" to "mSPARK MOMBASA DUKAS T1"

class Analyser():
    def authenticate(self):
        Authenticator.authenticate(self)

        
    def get_chats_list(self):
        self.authenticate()
        file_list = self.drive.ListFile({'q': "'%s' in parents and trashed=false" % settings.GCP_DRIVE_ID}).GetList()

        chats = []
        for file in file_list:
            chats.append({
                'google_id': file['id'],
                'web_content_link': file['webContentLink'],
                'title': file['title'],
                'datetime_created': file['createdDate'],
                'filesize': file['fileSize'],
            })

        return chats

    def process_uploaded_files(self):
        # 1. Get all the chats uploaded to the google drive
        # 2. Check if the file is already processed
        # 3. If not processed
        #   a. Check if the group name is changed. File title should match the group name from the first line
        #   b. Save the file to the DB
        #   b. Process the file saving the message from the bottom
        
        chats_list = self.get_chats_list()
        for chat in chats_list:
            self.chat_file_comments = None
            chat_file = self.pre_process_chatfile(chat)

            if chat_file is None or chat_file.status not in ['pending', 'to_reprocess']:
                if os.path.exists('tmpfiles/%s' % chat['title']): os.remove('tmpfiles/%s' % chat['title'])
                continue        # nothing to do with this chat file

    def pre_process_chatfile(self, chat):
        # given a chat object, preprocess it by fetching/creating a whatsapp group object and its associated file object
        try:
            chat_file = WhatsAppChatFile.objects.get(google_id=chat['google_id'])
        except WhatsAppChatFile.DoesNotExist:
            group_name = self.extract_group_name_from_filename(chat['title'])
            
            (group_creation_time, group_creator, line_group_name) = self.extract_group_attr_from_firstline(chat['google_id'], chat['title'])
            if group_creator is None:
                group_creator = "Error! Couldn't find the creator"

            if group_name is None and line_group_name is None:
                self.chat_file_comments = "I couldn't extract the group name of the the WhatsApp chat file '%s' (%s). I missed the group name from the filename as well as from the first line. I have skipped processing this file" % (chat['title'], chat['google_id'])
                email_settings = {
                    'template': 'emails/general-email.html',
                    'subject': '[%s] Corrupted group name of WhatsApp Chat' % settings.SITE_NAME,
                    'sender_email': settings.SENDER_EMAIL,
                    'recipient_email': settings.ADMIN_EMAILS,
                    'use_queue': getattr(settings, 'QUEUE_EMAILS', False),
                    'title': 'Corrupt group name',
                    'message': self.chat_file_comments,
                }
                notify = Notification()
                
                if settings.DEBUG: notify.send_sentry_message(self.chat_file_comments, 'info')
                else: notify.send_email(email_settings)
                self.save_chat_file(chat, 'failed_preprocessing')
            
                return None

            if group_name is None: group_name = line_group_name
            group_name = group_name.strip()

            try:
                group = WhatsAppGroup.objects.get(group_name=group_name)
            except WhatsAppGroup.DoesNotExist:
                # we have to create the new group
                # Expecting a time like '3/17/20, 9:38 PM'
                try:
                    ext_datetime = self.extract_date_from_message(group_creation_time, '%m/%d')
                except ValueError as e:
                    if str(e) == "Possible Wrong Date Format": ext_datetime = self.extract_date_from_message(group_creation_time, '%d/%m')
                    else: raise
                except Exception: raise

                group = WhatsAppGroup(
                    group_name=group_name,
                    datetime_created=ext_datetime,
                    created_by=group_creator
                )
                group.full_clean()
                group.save()

            try:
                chat_file = self.save_chat_file(chat, 'pending', group)
            except Exception as e:
                # In case it fails... just move on
                if settings.DEBUG: terminal.tprint(str(e), 'fail')
                sentry_sdk.capture_exception(e)
                return None

        return chat_file

    def save_chat_file(self, chat, status_, group=None):
        try:
            file = WhatsAppChatFile.objects.get(google_id=chat['google_id'])
            file.status = status_
            file.save()

            return file
        except WhatsAppChatFile.DoesNotExist:
            chat_file = WhatsAppChatFile(
                group=group,
                google_id=chat['google_id'],
                web_content_link=chat['web_content_link'],
                title=chat['title'],
                datetime_created=chat['datetime_created'],
                filesize=chat['filesize'],
                status=status_,
                comments=self.chat_file_comments
            )
            chat_file.full_clean()
            chat_file.save()

            return chat_file

    def extract_group_name_from_filename(self, filename):
        # Given a file, extract the group name from the filename
        # The file name should be like 'WhatsApp Chat with SMART DUKA WINNERS.txt' where SMART DUKA WINNERS is the group name
        try:
            name = re.findall('^WhatsApp\s+Chat\s+with\s+(.+)\.txt$', filename, re.IGNORECASE)
            if len(name) == 0:
                # I cant extract the group name from the file.... so get the name from the first line
                return None

            return name[0]

        except Exception as e:
            raise

    def download_file(self, file_id, file_name):
        print('Downloading the file %s' % file_name)
        self.authenticate()
        file = self.drive.CreateFile({'id': file_id})

        # Create tmpfiles directory
        if(os.path.exists('tmpfiles') == False):
            os.makedirs('tmpfiles') 

        file.GetContentFile('tmpfiles/%s' % file_name, 'text/plain')

    def extract_group_attr_from_firstline(self, file_id, file_name):
        if not os.path.exists('tmpfiles/%s' % file_name):
            self.download_file(file_id, file_name)

        with open('tmpfiles/%s' % file_name, 'rt') as fh:
            # get the first line and check whether we have something like '3/17/20, 9:38 PM - Rachel Tns created group "SMART DUKA WINNERS"'
            first_line = fh.readline().strip()
            second_line = fh.readline().strip()

        if re.match(intro_regex, first_line, re.IGNORECASE):
            group_name_line = second_line
        else: group_name_line = first_line

        

        group_attr = re.findall(group_creator_regex, group_name_line, re.IGNORECASE)

        if len(group_attr) == 0 or len(group_attr[0]) != 3:
            self.chat_file_comments = "The first line from the WhatsApp chat '%s' (%s) is corrupt as I couldn't extract the group creator and the group name from the line '%s'. I have skipped processing this file" % (file_name, file_id, group_name_line)
            email_settings = {
                'template': 'emails/general-email.html',
                'subject': '[%s] Corrupted first line of WhatsApp Chat' % settings.SITE_NAME,
                'sender_email': settings.SENDER_EMAIL,
                'recipient_email': settings.ADMIN_EMAILS,
                'use_queue': getattr(settings, 'QUEUE_EMAILS', False),
                'title': 'Corrupt first line',
                'message': self.chat_file_comments,
            }
            notify = Notification()

            if settings.DEBUG: notify.send_sentry_message(self.chat_file_comments, 'info')
            else: notify.send_email(email_settings)

            return None, None, None

        return group_attr[0]

    def fetch_groups_info(self):
        to_return = {}
        all_groups = GroupDailyStats.objects.select_related('group').values('group_id').annotate(group_name=F('group__group_name'), created_by=F('group__created_by'), new_users_=Sum('new_users'), left_users_=Sum('left_users'), no_messages_=Sum('no_messages'), no_images_=Sum('no_images'), no_links_=Sum('no_links'), date_created=functions.Cast('group__datetime_created', output_field=CharField() )).all()

        to_return['group_info'] = []

        for grp in all_groups:
            grp['group_id'] = my_hashids.encode(grp['group_id'])
            to_return['group_info'].append(grp)
        
        return to_return

    def get_all_chats(self, request):
        try:
            start = int(request.POST['start'])
            length_ = int(request.POST['length'])

            filters = Q()
            if 'search[value]' in request.POST and request.POST['search[value]'] != '':
                filters = Q(group__group_name__icontains=request.POST['search[value]']) | Q(title__icontains=request.POST['search[value]'])


            all_items_ = WhatsAppChatFile.objects.select_related('group').filter(filters).values('id', 'google_id', 'web_content_link', 'title', 'datetime_created', 'filesize', 'status', 'comments', group_name=F('group__group_name')).order_by('-datetime_created').all()[start:start+length_]

            all_filtered_items = WhatsAppChatFile.objects.select_related('group').filter(filters).values('id', 'google_id', 'web_content_link', 'title', 'datetime_created', 'filesize', 'status', 'comments', group_name=F('group__group_name')).order_by('-datetime_created').all()

            all_items = list(all_items_)
            
            return {
                'data': all_items, # JsonResponse(all_items, safe=False),
                "recordsTotal": WhatsAppChatFile.objects.count(),
                "draw": int(request.POST['draw']),
                "recordsFiltered": len(all_filtered_items)
            }

        except Exception as e:
            if settings.DEBUG: terminal.tprint(str(e), 'fail')
            sentry_sdk.capture_exception(e)
            raise Exception('There was an error while fetching data from the database')

    def process_pending_chats(self):
        try:
            all_items = WhatsAppChatFile.objects.exclude(group=None).filter(status__in=('pending', 'to_reprocess')).values('id', 'google_id', 'title', 'group_id').all()
            for item in all_items:
                try:
                    self.process_chat(item, '%m/%d')
                except ValueError as e:
                    if str(e) == "Possible Wrong Date Format": self.process_chat(item, '%d/%m')
                    else: raise
                except Exception: raise

        except Exception as e:
            if settings.DEBUG: terminal.tprint(str(e), 'fail')
            sentry_sdk.capture_exception(e)
            raise

    def process_chat(self, chat_file, date_format):
        try:
            google_id = chat_file['google_id']
            filename = chat_file['title']
            chat_id = chat_file['id']
            group_id = chat_file['group_id']

            filename = 'cur_processing_file.txt' if filename is None else filename

            if not os.path.exists('tmpfiles/%s' % filename):
                self.download_file(google_id, filename)

            i = 0
            with open('tmpfiles/%s' % filename, 'rt') as fh:
                print('\n```````````````\nProcessing %s' % filename)
                transaction.set_autocommit(False)
                self.cur_file_messages = []
                all_chats = []
                group_name_changes = []
                cur_message = None
                prev_message = None
                prev_date = None
                found_creator = False
                found_disclaimer = False
                cur_day_details = None
                all_statuses = []

                for line_ in fh:
                    i += 1
                    if line_.strip() == '': continue
                    line_ = line_.strip()

                    if found_creator == False and re.match(intro_regex, line_, re.IGNORECASE):
                        found_creator = True
                        continue

                    if found_disclaimer == False and re.match(group_creator_regex, line_, re.IGNORECASE):
                        found_disclaimer = True
                        continue

                    is_ok = False

                    # extract the date of the message
                    if re.findall('^\d{1,2}\/\d{1,2}\/\d{1,2}', line_, re.IGNORECASE):
                        # we have some date...
                        cur_line_parts = re.findall(msg_line_regex, line_, re.IGNORECASE)
                        cur_date = self.extract_date_from_message(line_, date_format)

                       

                        if len(cur_line_parts) == 0:
                            # we have a message starting with a date but not really a message
                            #check if its a group name change
                            if len(re.findall(group_name_change_regex, line_, re.IGNORECASE)):
                                name_changes = re.findall(group_name_change_regex, line_, re.IGNORECASE)[0]
                                mssg_date = self.extract_date_from_message(line_, date_format)
                                group_name_changes.append({'date_time': '%s' % mssg_date.astimezone(get_localzone()), 'from': name_changes[1], 'to': name_changes[2]})
                                continue

                            cur_message = self.process_dated_non_message(line_)
                            if cur_message is None:
                                self.cur_file_messages.append("Line %d: I don't know how to process the message: '%s'" % (i, line_))
                                continue
                            elif cur_message == -1:
                                # some messages are not important and can be ignored
                                continue

                        elif len(cur_line_parts) == 1 and len(cur_line_parts[0]) == 3:
                            cur_message = cur_line_parts[0]

                        else:
                            # The date, time and user wasnt caught... so inform people
                            self.cur_file_messages.append("Line %d: I couldn't extract the date, time and sender in the line '%s'" % (i, line_))
                            continue
                    else: 
                        # most likely we have a chat split over multiple lines
                        if cur_message is None:
                            # we prolly have a chat continuation but we dont have the first parts of the message
                            # raise an exception
                            self.cur_file_messages.append("Line %d: I think I have continuation of a message, but I couldn't get the first part.'%s'" % (i, line_))
                        else:
                            prev_message = (prev_message[0], prev_message[1], '%s\n%s' % (prev_message[2], line_))

                        continue

                    if prev_message is not None:
                        (is_event, has_image, has_link, user_add, user_left, removed_user, emojis) = self.process_chat_message(prev_message[2])

                        if cur_day_details is None:
                            cur_day_details = { 'date_': None, 'new_users': 0, 'left_users': 0, 'removed_users': 0, 'no_messages': 0, 'no_images': 0, 'no_links': 0, 'emojis': '', 'users': {}, 'active_hrs': {} }
                            cur_day_details['date_'] = prev_date.strftime('%Y-%m-%d')

                        mssg_hr = prev_date.strftime('%H')

                        # add the parameters
                        if is_event == False:
                            cur_day_details['no_messages'] += 1

                            if prev_message[1] not in cur_day_details['users']:
                                cur_day_details['users'][prev_message[1]] = { 'no_messages': 0, 'no_images': 0, 'no_links': 0, 'emojis': '', 'active_hrs': {}, 'messages': [] }
                                
                            cur_day_details['users'][prev_message[1]]['no_messages'] += 1

                            # add messaging hours
                            if mssg_hr not in cur_day_details['active_hrs']:
                                cur_day_details['active_hrs'][mssg_hr] = 0
                            
                            cur_day_details['active_hrs'][mssg_hr] += 1

                            if mssg_hr not in cur_day_details['users'][prev_message[1]]['active_hrs']:
                                cur_day_details['users'][prev_message[1]]['active_hrs'][mssg_hr] = 0

                            cur_day_details['users'][prev_message[1]]['active_hrs'][mssg_hr] += 1

                            if emojis != '':
                                cur_day_details['users'][prev_message[1]]['emojis'] += emojis
                                cur_day_details['emojis'] += emojis

                            elif has_link:
                                cur_day_details['users'][prev_message[1]]['no_links'] += 1
                                cur_day_details['no_links'] += 1

                            elif has_image:
                                cur_day_details['users'][prev_message[1]]['no_images'] += 1
                                cur_day_details['no_images'] += 1

                            # cur_day_details['users'][prev_message[1]]['messages'].append((prev_date.strftime('%Y-%m-%d %H:%M:%S.%f+%z'), prev_message[1], prev_message[2]))
                            cur_day_details['users'][prev_message[1]]['messages'].append(('%s' % prev_date.astimezone(get_localzone()), prev_message[1], prev_message[2]))

                        elif user_add: cur_day_details['new_users'] += user_add
                        elif user_left: cur_day_details['left_users'] += 1
                        elif removed_user: cur_day_details['removed_users'] += 1
                        
                        if cur_date.strftime('%Y-%m-%d') != prev_date.strftime('%Y-%m-%d'):
                            # we have a new day
                            status_ = self.save_day_stats(cur_day_details, chat_file['group_id'], chat_file['id'])
                            if status_ not in all_statuses: all_statuses.append(status_)
                            cur_day_details = None

                    prev_message = (cur_message[0], cur_message[1].strip(' -'), cur_message[2])
                    prev_date = cur_date
                    # if i == 100: break

                if len(self.cur_file_messages) != 0:
                    email_settings = {
                        'template': 'emails/general-email.html',
                        'subject': '[%s] Error while processing message' % settings.SITE_NAME,
                        'sender_email': settings.SENDER_EMAIL,
                        'recipient_email': settings.ADMIN_EMAILS,
                        'use_queue': getattr(settings, 'QUEUE_EMAILS', False),
                        'title': 'Error while processing message',
                        'message': '<br />'.join(self.cur_file_messages),
                    }
                    notify = Notification()

                    notify.send_email(email_settings)
                    # if settings.DEBUG: print('\n'.join(self.cur_file_messages)) # notify.send_sentry_message(self.chat_file_comments, 'info')
                    # else: notify.send_email(email_settings)

                # print(group_name_changes)
                print('Lines in %s = %d' %(filename, i))
                self.save_group_name_changes(group_name_changes, chat_file['group_id'])
                # update this file that it is processed
                chat_file = WhatsAppChatFile.objects.get(id=chat_file['id'])
                chat_file.status = 'processed'
                chat_file.save()
                transaction.commit()

        except ValueError as e:
            transaction.rollback()
            raise ValueError(str(e))

        except Exception as e:
            transaction.rollback()
            if settings.DEBUG: terminal.tprint(str(e), 'fail')
            sentry_sdk.capture_exception(e)
            raise Exception('There was an error while processing the chat with id %s' % google_id)

    def emoji_list(self, text):
        y = ''.join(c for c in text if c in emoji.UNICODE_EMOJI['en'])
        # if y != '': print(y)
        return y

        emoji_list = []
        data = re.findall(r'\X', text)
        for word in data:
            if any(char in emoji.UNICODE_EMOJI for char in word):
                emoji_list.append(word)
        return emoji_list

    def emoji_count(self, emojis):
        al_emojis = {}
        for c in emojis:
            if c not in al_emojis: al_emojis[c] = 0
            al_emojis[c] += 1

        return al_emojis

    def process_chat_message(self, message):
        is_event = False
        has_image = False
        has_link = False
        user_add = None
        user_left = False
        removed_user = False

        # check for links, emojis and images
        if len(re.findall('\<Media omitted\>', message, re.IGNORECASE)) != 0: has_image = True
        elif len(re.findall(url_regex, message, re.IGNORECASE)) != 0: has_link = True
        elif len(re.findall(user_add_regex, message, re.IGNORECASE)) != 0:
            user_added = re.findall(user_add_regex, message, re.IGNORECASE)
            if len(user_added) == 1 and len(user_added[0]) == 2 and user_added[0][1] != '':
                try:
                    user_add = len(user_added[0][1].split('added')[1].split(', '))
                except IndexError:
                    user_add = 1
                except: raise

                is_event = True
        elif len(re.findall(user_left_regex, message, re.IGNORECASE)) != 0:
            user_lefted = re.findall(user_left_regex, message, re.IGNORECASE)
            if len(user_lefted) == 1 and len(user_lefted[0]) == 3:
                user_left = True
                is_event = True
        elif len(re.findall(removed_users_regex, message, re.IGNORECASE)) != 0:
            user_removed = re.findall(removed_users_regex, message, re.IGNORECASE)
            if len(user_removed) == 1 and len(user_removed[0]) == 3:
                removed_user = True
                is_event = True
        
        emojis = self.emoji_list(message)
        # print(emoji_stats)

        # if len(re.findall('added', message, re.IGNORECASE)) != 0 and is_prev_event == False:
        #     print(prev_message)
        #     print(is_prev_event)
        #     
        return (is_event, has_image, has_link, user_add, user_left, removed_user, emojis)

    def extract_date_from_message(self, message, date_format):
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

    def process_dated_non_message(self, chat_mssg):
        reformatted = None
        user_added = re.findall(user_add_regex, chat_mssg, re.IGNORECASE)
        user_lefted = re.findall(user_left_regex, chat_mssg, re.IGNORECASE)
        user_removed = re.findall(removed_users_regex, chat_mssg, re.IGNORECASE)
        # print('\n```````````````\n%s' % chat_mssg)
        # print(user_added)
        # print(user_lefted)
        # print(user_removed)

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

    def save_day_stats(self, cur_day_details, group_id, chat_file_id):
        # 1. Save the group
        # 2. Save the group daily stats
        # 3. Save the user daily stats
        max_count = {'hr': -1, 'count': -1}
        for hr_, count_ in cur_day_details['active_hrs'].items(): max_count={'hr':hr_, 'count':count_} if count_>max_count['count'] else max_count
        try:
            sgs = GroupDailyStats.objects.filter(group_id=group_id, stats_date=cur_day_details['date_']).get()

            # ok some stats exist, check if they all check out
            if(
                sgs.new_users == cur_day_details['new_users'] and sgs.left_users == cur_day_details['left_users'] and sgs.most_active_hr == max_count['hr'] and sgs.emojis == cur_day_details['emojis'] and
                sgs.no_messages == cur_day_details['no_messages'] and sgs.no_images == cur_day_details['no_images'] and sgs.no_links == cur_day_details['no_links']
            ):
                # we have a duplicate stat from another file... ignore it for noww
                return 'Duplicate GroupStats'
            else:
                # we have a mismatch.... so lets email the admins
                # sgs_serial= GroupDailyStatsSerializer(sgs, many=True)
                # print(json.dumps(sgs_serial.data, indent=3))
                cur_file = WhatsAppChatFile.objects.get(id=chat_file_id)
                cur_filename = cur_file.title

                first_file = WhatsAppChatFile.objects.get(id=sgs.chat_file_id)
                first_filename = first_file.title
                
                group = WhatsAppGroup.objects.get(id=sgs.group_id)
                group_name = group.group_name

                sgs_data = {
                    'new_users': sgs.new_users, 'left_users': sgs.left_users, 'most_active_hr': sgs.most_active_hr, 'emojis': sgs.emojis, 'no_messages': sgs.no_messages, 'no_images': sgs.no_images, 'no_links': sgs.no_links
                }

                stats_date = cur_day_details['date_']
                current_stats = {
                    'stats_date': cur_day_details['date_'],
                    'new_users': cur_day_details['new_users'],
                    'left_users': cur_day_details['left_users'],
                    'most_active_hr': max_count['hr'],
                    'emojis': cur_day_details['emojis'],
                    'no_messages': cur_day_details['no_messages'],
                    'no_images': cur_day_details['no_images'],
                    'no_links': cur_day_details['no_links']
                }
                
                stats_mismatch_comments = "There exists a group daily stats record for '%s' group for '%s' that was extracted from '%s'. However I have other stats for the same group for the same day extracted from '%s'. I don't know what to do. <br/><strong>Stats from %s</strong><br/><pre>%s</pre><br/><br/><strong>Stats from %s</strong><br/><pre>%s</pre><br/>" % (group_name, stats_date, first_filename, cur_filename, first_filename, json.dumps(sgs_data, indent=3), cur_filename, json.dumps(current_stats, indent=3))

                self.cur_file_messages.append(stats_mismatch_comments)
                notify = Notification()
                notify.send_sentry_message(stats_mismatch_comments, 'info', [{'tag': 'saved_stats', 'value': sgs_data}, {'tag':'new_stats', 'value': json.dumps(current_stats, indent=3)}])
                return 'Mismatched GroupStats'

        except GroupDailyStats.DoesNotExist: pass   # the stats dont exist which is good

        grp_stats = GroupDailyStats(
            group_id=group_id,
            chat_file_id=chat_file_id,
            stats_date=cur_day_details['date_'],
            new_users=cur_day_details['new_users'],
            left_users=cur_day_details['left_users'],
            most_active_hr=max_count['hr'],
            emojis=cur_day_details['emojis'],
            no_messages=cur_day_details['no_messages'],
            no_images=cur_day_details['no_images'],
            no_links=cur_day_details['no_links']
        )
        grp_stats.full_clean()
        grp_stats.save()

        for u_name_phone, us in cur_day_details['users'].items():
            us_count = {'hr': -1, 'count': -1}
            for hr_, count_ in us['active_hrs'].items(): us_count={'hr':hr_, 'count':count_} if count_>us_count['count'] else us_count

            try:
                uds = UserDailyStats.objects.filter(name_phone=u_name_phone, group_id=group_id, stats_date=cur_day_details['date_']).get()

                # check if its a duplicate
                if uds.most_active_hr == us_count['hr'] and uds.emojis == us['emojis'] and uds.no_messages == us['no_messages'] and uds.no_images == us['no_images'] and uds.no_links == us['no_links']:
                    return 'Duplicate UserStats'
                else:
                    cur_file = WhatsAppChatFile.objects.get(id=chat_file_id)
                    cur_filename = cur_file.title

                    first_file = WhatsAppChatFile.objects.get(id=uds.chat_file_id)
                    first_filename = first_file.title
                    
                    group = WhatsAppGroup.objects.get(id=uds.group_id)
                    group_name = group.group_name

                    uds_data = {
                        'most_active_hr': uds.most_active_hr, 'emojis': uds.emojis, 'no_messages': uds.no_messages, 'no_images': uds.no_images, 'no_links': uds.no_links
                    }

                    stats_date = cur_day_details['date_']
                    current_stats = {
                        'most_active_hr': us_count['hr'],
                        'emojis': us['emojis'],
                        'no_messages': us['no_messages'],
                        'no_images': us['no_images'],
                        'no_links': us['no_links']
                    }
                    
                    stats_mismatch_comments = "There exists a group daily stats record for '%s' group for '%s' that was extracted from '%s'. However I have other stats for the same group for the same day extracted from '%s'. I don't know what to do. <br/><strong>Stats from %s</strong><br/><pre>%s</pre><br/><br/><strong>Stats from %s</strong><br/><pre>%s</pre><br/>" % (group_name, stats_date, first_filename, cur_filename, first_filename, json.dumps(uds_data, indent=3), cur_filename, json.dumps(current_stats, indent=3))

                    self.cur_file_messages.append(stats_mismatch_comments)
                    notify = Notification()
                    notify.send_sentry_message(stats_mismatch_comments, 'info', [{'tag': 'saved_stats', 'value': uds_data}, {'tag':'new_stats', 'value': json.dumps(current_stats, indent=3)}])

                    return 'Mismatched UserStats'

            except UserDailyStats.DoesNotExist: pass

            stats_ = UserDailyStats(
                name_phone=u_name_phone,
                group_id=group_id,
                chat_file_id=chat_file_id,
                stats_date=cur_day_details['date_'],
                most_active_hr=us_count['hr'],
                emojis=us['emojis'],
                no_messages=us['no_messages'],
                no_images=us['no_images'],
                no_links=us['no_links']
            )
            stats_.full_clean()
            stats_.save()

            for mssg in us['messages']:
                ml = MessageLog(
                    chat_file_id=chat_file_id,
                    user=stats_,
                    datetime_sent=mssg[0],
                    message=mssg[2]
                )
                ml.full_clean()
                ml.save()

                # raise Exception('tarn tramps %s ' % json.dumps(cur_day_details))

        return 'Saved'

    def save_group_name_changes(self, grp_names, group_id):
        for name_ in grp_names:
            name_change = GroupNameChanges(
                group_id=group_id,
                change_datetime=name_['date_time'],
                from_name=name_['from'],
                to_name=name_['to']
            )
            name_change.full_clean()
            name_change.save()

    def fetch_group_meta(self, group_id, date_range):
        grp = WhatsAppGroup.objects.get(id=group_id)
        last_date = GroupDailyStats.objects.filter(group_id=group_id).values('stats_date').order_by('-stats_date').first()
        first_date = GroupDailyStats.objects.filter(group_id=group_id).values('stats_date').order_by('stats_date').first()
        if last_date is None: return {'info_message': 'The processed database is empty. Please run the initial processing.', 'empty_db': True}
        to_return = self.determine_dateranges(date_range, first_date['stats_date'], last_date['stats_date'])
        to_return['group_name'] = grp.group_name
        s_date = to_return['ss_date']
        e_date = to_return['ee_date']

        # most active day
        most_active_day = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).values('stats_date', 'no_messages').order_by('-no_messages').first()
        if date_range is None:
            to_return['info_message'] = 'Date range is not defined. Showing analysis for the period %s - %s' % (to_return['min_date'], to_return['max_date'])
            

        elif most_active_day is None:
            # put a good time range
            to_return['info_message'] = 'No records were found in the specified time period %s - %s. The last chat date is %s. Showing analysis for the period %s - %s' % (to_return['s_date'], to_return['e_date'], to_return['max_date'], to_return['min_date'], to_return['max_date'])
            to_return['s_date'] = to_return['min_date']
            to_return['e_date'] = to_return['max_date']
            s_date = datetime.strptime(to_return['s_date'], '%d/%m/%Y')
            e_date = datetime.strptime(to_return['e_date'], '%d/%m/%Y')

            most_active_day = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).values('stats_date', 'no_messages').order_by('-no_messages').first()
            

        period_stats = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).aggregate(lefties=Sum('left_users'), joinies=Sum('new_users'), images_count=Sum('no_images'), links_count=Sum('no_links'), messages_count=Sum('no_messages'))

        total_users = GroupDailyStats.objects.filter(stats_date__lte=e_date, group_id=group_id).aggregate(lefties=Sum('left_users'), joinies=Sum('new_users'))
        to_return['name_changes'] = GroupNameChanges.objects.filter(group_id=group_id).extra(select={'change_datetime_':"DATE_FORMAT(change_datetime, '%%b %%d %%Y, %%r')"}).values('to_name', 'from_name', 'change_datetime_').annotate(tn=Count('change_datetime')).order_by('-change_datetime').all()

        # most active user
        most_active_user = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).values('name_phone').annotate(sum_messages=Sum('no_messages')).order_by('-sum_messages').first()
        
        # most active time of the day
        most_active_time = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).exclude(most_active_hr=-1).values('most_active_hr').annotate(messages_count=Count('most_active_hr')).order_by('-messages_count').first()

        # active days
        datelist = pd.date_range(s_date, e_date).tolist()
        all_data_df = pd.DataFrame(list( GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).extra(select={'stats_date_':"DATE_FORMAT(stats_date, '%%Y-%%m-%%d')"}).values('stats_date_', 'no_messages').order_by('stats_date_').all() ))
        
        active_users_df = pd.DataFrame(list( UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).extra(select={'stats_date_':"DATE_FORMAT(stats_date, '%%Y-%%m-%%d')"}).values('stats_date_').annotate(no_users=Count('name_phone')).order_by('stats_date_').all() ))
        
        recs = all_data_df.set_index('stats_date_').T.to_dict('records')[0]
        all_users = active_users_df.set_index('stats_date_').T.to_dict('records')[0]

        cool_dates = []
        cool_messages = []
        cool_users = []
        for date_ in datelist:
            cool_date = date_.strftime('%Y-%m-%d')
            cool_dates.append(cool_date)

            if str(cool_date) not in recs: cool_messages.append(0)
            else: cool_messages.append(recs[cool_date])

            if str(cool_date) not in all_users: cool_users.append(0)
            else: cool_users.append(all_users[cool_date])

        # emojis
        sumd_emojis = {}
        emoji_count = 0
        all_emojis = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).values('emojis').all()
        for al_ in all_emojis:
            emoji_stats = self.emoji_count(al_['emojis'])
            for k in set(emoji_stats): emoji_count += emoji_stats.get(k, 0)

            sumd_emojis = {k: emoji_stats.get(k, 0) + sumd_emojis.get(k, 0) for k in set(emoji_stats) | set(sumd_emojis) }

        to_return['emojis'] = [ {'e': k, 'y': v} for k, v in sorted(sumd_emojis.items(), key=lambda x: x[1], reverse=True) ]
        to_return['emojis_count'] = emoji_count
        to_return['active_user'] = most_active_user
        to_return['no_users'] = total_users['joinies'] - total_users['lefties']
        to_return['totals'] = emoji_count + period_stats['images_count'] + period_stats['links_count'] + period_stats['messages_count']
        to_return['most_active_day'] = most_active_day['stats_date'].strftime('%d/%m/%Y, %A')
        to_return['most_active_time'] = most_active_time
        to_return['active_dates'] = {'dates': cool_dates, 'messages': cool_messages, 'users': cool_users}

        to_return = {**to_return, **period_stats}
        
        return to_return

    def fetch_user_meta(self, group_id, user_, date_range):
        grp = WhatsAppGroup.objects.get(id=group_id)
        last_date = UserDailyStats.objects.filter(group_id=group_id, name_phone=user_).values('stats_date').order_by('-stats_date').first()
        first_date = UserDailyStats.objects.filter(group_id=group_id, name_phone=user_).values('stats_date').order_by('stats_date').first()
        if last_date is None: return {'info_message': 'The processed database is empty. Please run the initial processing.', 'empty_db': True}
        to_return = self.determine_dateranges(date_range, first_date['stats_date'], last_date['stats_date'])
        to_return['user_name'] = '%s of %s' % (user_, grp.group_name)
        s_date = to_return['ss_date']
        e_date = to_return['ee_date']

        # most active day
        most_active_day = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).values('stats_date', 'no_messages').order_by('-no_messages').first()
        if date_range is None:
            to_return['info_message'] = 'Date range is not defined. Showing analysis for the period %s - %s' % (to_return['min_date'], to_return['max_date'])

        elif most_active_day is None:
            # put a good time range
            to_return['info_message'] = 'No records were found in the specified time period %s - %s. The last chat date is %s. Showing analysis for the period %s - %s' % (to_return['s_date'], to_return['e_date'], to_return['max_date'], to_return['min_date'], to_return['max_date'])
            to_return['s_date'] = to_return['min_date']
            to_return['e_date'] = to_return['max_date']
            s_date = datetime.strptime(to_return['s_date'], '%d/%m/%Y')
            e_date = datetime.strptime(to_return['e_date'], '%d/%m/%Y')

            most_active_day = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).values('stats_date', 'no_messages').order_by('-no_messages').first()
            
        period_stats = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).aggregate(images_count=Sum('no_images'), links_count=Sum('no_links'), messages_count=Sum('no_messages'))

        # group interaction
        grp_stats = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).aggregate(messages_count=Sum('no_messages'))
        to_return['grp_interaction'] = float('{0:.1f}'.format( ((period_stats['messages_count'] / grp_stats['messages_count']) * 100) ))

        # most active time of the day
        most_active_time = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).exclude(most_active_hr=-1).values('most_active_hr').annotate(messages_count=Count('most_active_hr')).order_by('-messages_count').first()

        # active days
        datelist = pd.date_range(s_date, e_date).tolist()
        all_ = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).extra(select={'stats_date_':"DATE_FORMAT(stats_date, '%%Y-%%m-%%d')"}).values('stats_date_', 'no_messages').order_by('stats_date_').all()
        all_data_df = pd.DataFrame(list( all_ ))
        
        recs = all_data_df.set_index('stats_date_').T.to_dict('records')[0]
        cool_dates = []
        cool_messages = []
        for date_ in datelist:
            cool_date = date_.strftime('%Y-%m-%d')
            cool_dates.append(cool_date)

            if str(cool_date) not in recs: cool_messages.append(0)
            else: cool_messages.append(recs[cool_date])

        # emojis
        sumd_emojis = {}
        emoji_count = 0
        all_emojis = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).values('emojis').all()
        for al_ in all_emojis:
            emoji_stats = self.emoji_count(al_['emojis'])
            for k in set(emoji_stats): emoji_count += emoji_stats.get(k, 0)

            sumd_emojis = {k: emoji_stats.get(k, 0) + sumd_emojis.get(k, 0) for k in set(emoji_stats) | set(sumd_emojis) }

        # actual messages
        all_messages = list(MessageLog.objects.select_related('user').filter(user__stats_date__gte=s_date, user__stats_date__lte=e_date, user__group_id=group_id, user__name_phone=user_).extra(select={'dt':"DATE_FORMAT(datetime_sent, '%%Y-%%m-%%d %%H:%%i')"}).values('dt').annotate(mssg=F('message')).order_by('datetime_sent').all())

        to_return['emojis'] = [ {'e': k, 'y': v} for k, v in sorted(sumd_emojis.items(), key=lambda x: x[1], reverse=True) ]
        to_return['all_messages'] = all_messages
        to_return['emojis_count'] = emoji_count
        to_return['most_active_day'] = most_active_day['stats_date'].strftime('%d/%m/%Y, %A')
        to_return['most_active_time'] = most_active_time
        to_return['active_dates'] = {'dates': cool_dates, 'messages': cool_messages}
        
        to_return = {**to_return, **period_stats}
        
        return to_return

    def fetch_all_meta(self, date_range):
        last_date = GroupDailyStats.objects.values('stats_date').order_by('-stats_date').first()
        first_date = GroupDailyStats.objects.values('stats_date').order_by('stats_date').first()
        if last_date is None: return {'info_message': 'The processed database is empty. Please run the initial processing.', 'empty_db': True}
        to_return = self.determine_dateranges(date_range, first_date['stats_date'], last_date['stats_date'])
        s_date = to_return['ss_date']
        e_date = to_return['ee_date']

        # Whatsapp groups
        emoji_count = 0
        all_emojis = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).values('emojis').all()
        for al_ in all_emojis:
            emoji_stats = self.emoji_count(al_['emojis'])
            for k in set(emoji_stats): emoji_count += emoji_stats.get(k, 0)

        to_return['file_status'] = { st_[0]: 0 for st_ in STATUS_CHOICES }
        status_counts = list(WhatsAppChatFile.objects.values('status').annotate(s_count=Count('status')).all())
        all_count = 0
        for st_ in status_counts:
            to_return['file_status'][st_['status']] = st_['s_count']
            all_count += st_['s_count']

        to_return['perc_processed'] = float('{0:.1f}'.format( (( to_return['file_status']['processed'] / all_count ) * 100) )) 
        to_return['no_groups'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).values('group_id').annotate(g_count=Count('group_id')).count()
        to_return['no_users'] = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).values('group_id', 'name_phone').annotate(g_count=Count('group_id'), u_count=Count('name_phone')).count()
        to_return['no_messages'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).aggregate(g_count=Sum('no_messages'))['g_count']
        to_return['no_images'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).aggregate(g_count=Sum('no_images'))['g_count']
        to_return['no_links'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).aggregate(g_count=Sum('no_links'))['g_count']
        to_return['no_emojis'] = emoji_count

        return to_return

    def determine_dateranges(self, date_range, first_date, last_date):
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

    def fetch_engaged_users(self, request):
        start = int(request.POST['start'])
        length_ = int(request.POST['length'])

        if 'search[value]' in request.POST and request.POST['search[value]'] != '':
            filters = Q(name_phone__icontains=request.POST['search[value]']) | Q(group__group_name__icontains=request.POST['search[value]'])

        else:
            filters = Q()

        if 'order[0][column]' not in request.POST:
            order_col = 'id' 
        else:
            if request.POST['order[0][column]'] == '0': order_col = 'id'
            else:
                order_dir = '' if request.POST['order[0][dir]'] == 'asc' else '-'
                order_col = '%s%s' % (order_dir, request.POST['columns[%s][data]' % request.POST['order[0][column]']])

            # filters = reduce(lambda q, f: q | Q(creator=f), filters_, Q())

        all_items = UserDailyStats.objects.select_related('group').filter(filters).values('name_phone', 'group_id', 'group__group_name').annotate(name_phone_=Count('name_phone'), group_id_=Count('group_id'), no_messages=Sum('no_messages'), no_images=Sum('no_images'), no_links=Sum('no_links'), group_name=F('group__group_name')).order_by(order_col)
        filtered_items = all_items[start:start+length_]
        all_filtered_items = len(all_items)

        filtered_items_ = []
        for fi in filtered_items:
            fi['group_id'] = my_hashids.encode(fi['group_id'])
            filtered_items_.append(fi)
        
        returnees_ = {
            'data': filtered_items_, # JsonResponse(all_items, safe=False),
            "recordsTotal": UserDailyStats.objects.values('group_id', 'name_phone').annotate(g_count=Count('group_id'), u_count=Count('name_phone')).count(),
            "draw": int(request.POST['draw']),
            "recordsFiltered": all_filtered_items
        }

        return returnees_
        return {**to_return, **returnees_}
