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

from analyser.models import Personnel, WhatsAppGroup, WhatsAppChatFile, GroupDailyStats, UserDailyStats, MessageLog, GroupNameChanges, STATUS_CHOICES
from analyser.serializers import GroupDailyStatsSerializer
from analyser.common_tasks import Notification, Terminal

# Import regex constants
from analyser.chat.constants import *

# Import Authenticator Service
from analyser.chat.Authentication import Authenticator

# Import Database Service
from analyser.chat.DBService import DBService

# Import Utilities 
from analyser.chat.Utilities import Utilities

terminal = Terminal()
sentry_sdk.init(settings.SENTRY_DSN)
my_hashids = Hashids(min_length=5, salt=settings.SECRET_KEY)


# Instantiate DBService object
dbService = DBService()

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# You changed the subject from "mSPARK MSA DUKAS T1" to "mSPARK MOMBASA DUKAS T1"

class Analyser():
    def authenticate(self):
        Authenticator.authenticate(self)

      
    def get_chats_list(self):
        """ The function get_chats_list gets the list of chats from the drive all the chats are saved"""
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
        """ 1. Get all the chats uploaded to the google drive
         2. Check if the file is already processed
         3. If not processed
           a. Check if the group name is changed. File title should match the group name from the first line
           b. Save the file to the DB
           c. Process the file saving the message from the bottom"""
        
        chats_list = self.get_chats_list()
        for chat in chats_list:
            self.chat_file_comments = None
            chat_file = self.pre_process_chatfile(chat)

            if chat_file is None or chat_file.status not in ['pending', 'to_reprocess']:
                if os.path.exists('tmpfiles/%s' % chat['title']): os.remove('tmpfiles/%s' % chat['title'])
                continue        # nothing to do with this chat file

    def pre_process_chatfile(self, chat):
        """given a chat object, this function preprocess it by fetching/creating a whatsapp group object 
        and its associated file object """
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
        """ This function takes in chat, status and group and save the chat 
        """
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
                # Group name extraction from the file fails.... so get the name from the first line
                return None

            return name[0]

        except Exception as e:
            raise
    
    #Download the chat file
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
    
    # get group information
    def fetch_groups_info(self):
        return dbService.fetch_groups_info()
    
    #get all chats information
    def get_all_chats(self, request):
        return dbService.get_all_chats(request)

    #process chats that are yet to be processed   
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
        return Utilities.emoji_list(text)
        

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
            
        return (is_event, has_image, has_link, user_add, user_left, removed_user, emojis)

    def extract_date_from_message(self, message, date_format):
        return Utilities.extract_date_from_message(message, date_format)

    def process_dated_non_message(self, chat_mssg):
        return Utilities.process_dated_non_message(chat_mssg)
        

    def save_day_stats(self, cur_day_details, group_id, chat_file_id):
        # 1. Save the group
        # 2. Save the group daily stats
        # 3. Save the user daily stats

        return dbService.save_day_stats(cur_day_details, group_id, chat_file_id)
        

    def save_group_name_changes(self, grp_names, group_id):
        dbService.save_group_name_changes(grp_names, group_id)
        

    def fetch_group_meta(self, group_id, date_range):
        return dbService.fetch_group_meta(group_id, date_range)

    def fetch_user_meta(self, group_id, user_, date_range):
        return dbService.fetch_user_meta(group_id, user_, date_range)
        

    def fetch_all_meta(self, date_range):
        
        return dbService.fetch_all_meta(date_range)
        

    def fetch_engaged_users(self, request):
        return dbService.fetch_engaged_users(request)
        
