import csv
import random
import string
from datetime import datetime

from celery.schedules import crontab
from celery.task import task, periodic_task
from celery.utils.log import get_task_logger
from django.utils.timezone import make_aware

from chatgroup.models import ChatGroup
from email_handler.email_listener import Mail
from events.models import GroupEvent
from members.models import GroupMember
from message.models import GroupMessage
from uploads.models import ChatUpload, ChatUploadDetails, UPLOAD_STATUS
from utils.analysis import process_chat_file

logger = get_task_logger(__name__)


# tasks to analyse export files on upload
@task(name="analyse_export_chat_task")
def analyse_export_chat_task(chat_upload_id):
    """
    receive file, trigger analysis, save objects to models
    :param filepath:
    :param chat_group_name:
    :return:
    """
    logger.info("analyse_export_chat_task starting", str(chat_upload_id))

    # trigger analysis after file is saved
    # receive analysis file paths etc
    # save in models, events, messages, members

    def save_members_details(members_file, chat_group, upload_id):
        not_counted = []
        with open(members_file, 'r', encoding="utf-8") as f:
            csv_reader = csv.reader(f, delimiter=',')
            next(csv_reader)
            for row in csv_reader:
                username = row[1].strip()

                try:
                    member, created = GroupMember.objects.get_or_create(
                        username=username,
                        chat_group=chat_group)
                    if member:
                        member.upload_id = upload_id
                        member.save()

                    if created:
                        member.messages = row[2].strip().replace('"', '')
                        member.links = row[6].strip().replace('"', '')
                        member.top_links = row[9].strip().replace('"', '')
                        member.top_emojis = row[7].strip().replace('"', '')
                        member.words = row[3].strip().replace('"', '')
                        member.top_words = row[8].strip().replace('"', '')
                        member.emojis = row[4].strip().replace('"', '')
                        member.media = row[5].strip().replace('"', '')
                        member.upload_id = upload_id
                        member.save()

                except Exception as e:
                    print(e, username)
                    not_counted.append(username)
            print("Members not counted: ", not_counted)

    def save_messages_details(messages_file, chat_group, instance):
        with open(messages_file, 'r', encoding="utf-8") as f:
            csv_reader = csv.reader(f, delimiter=',')
            next(csv_reader)
            for row in csv_reader:
                try:
                    time_stamp = make_aware(datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S'))
                    sender = GroupMember.objects.filter(username=row[2], chat_group=chat_group)[0]
                    message = row[3]
                    group_message, created = GroupMessage.objects.get_or_create(
                        created=time_stamp, sender=sender, message_text=message.rstrip(), chat_group=chat_group)
                    if created:
                        group_message.save()
                    if group_message:
                        group_message.upload_id = instance
                        group_message.save()
                except Exception as e:
                    print(e)

    def get_or_create_group_chat(group_name, group_admin_name, group_creator, ts):
        '''
        get or create a gc if admin is new

        :param group_name: str
        :param group_admin_name: str
        :param group_creator: user.id
        :param ts: timestamp
        :return: groupchat chatgroup.id
        '''
        # create group admin
        member_id, m_created = GroupMember.objects.get_or_create(
            username=group_admin_name,
            is_group_admin=True)

        if m_created:
            member_id.date_joined = ts
            member_id.save()
        # create gc or return existing gc
        chat_group, g_created = ChatGroup.objects.get_or_create(
            name=group_name,
            date_created=ts,
            created_by=group_creator)
        if g_created:
            chat_group.save()

        if member_id:
            member_id.chat_group = chat_group
            member_id.save()

        return member_id

    def save_events_details(events_file, instance):
        try:
            attrition_types = ['created group', 'added', 'left', 'changed']
            group = 0
            with open(events_file, 'r', encoding="utf-8") as f:
                csv_reader = csv.reader(f, delimiter=',')
                next(csv_reader)
                for row in csv_reader:
                    time_stamp = row[1]
                    notification = row[2]
                    ts = make_aware(datetime.strptime(time_stamp, '%Y-%m-%d %H:%M:%S'))
                    username = ''

                    for a in attrition_types:
                        head, sep, tail = notification.partition(a)
                        if sep != '' and tail != '':
                            group_name = tail.strip().replace('"', '')

                            if a == 'created group':
                                if head.lower().strip() == 'you':
                                    head = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                                username = head
                                member = get_or_create_group_chat(
                                    group_name, username, instance.uploaded_by, ts
                                )
                                group = member.chat_group
                                event, created = GroupEvent.objects.get_or_create(
                                    event_type=a,
                                    event_details=tail,
                                    initiated_by=member,
                                    chat_group=group, event_date=ts, file_upload=instance
                                )
                                if event:
                                    event.save()

                            if a == 'added':

                                member_id, created = GroupMember.objects.get_or_create(
                                    username=username,
                                    chat_group=group
                                )
                                if member_id:
                                    member_id.date_joined = ts
                                    member_id.save()

                                event, created = GroupEvent.objects.get_or_create(
                                    event_type=a,
                                    event_details=tail,
                                    initiated_by=member_id,
                                    chat_group=group, event_date=ts, file_upload=instance
                                )

                                if event:
                                    event.save()

                            if a == 'left':
                                member_id, created = GroupMember.objects.get_or_create(
                                    username=username,
                                    chat_group=group
                                )

                                if created:
                                    member_id.date_joined = ts
                                    member_id.save()

                                event, created = GroupEvent.objects.get_or_create(
                                    event_type=a,
                                    event_details=head,
                                    initiated_by=member_id,
                                    chat_group=group, event_date=ts, file_upload=instance
                                )
                                if created:
                                    event.save()

                            # change or other event types
                            else:
                                member_id, created = GroupMember.objects.get_or_create(
                                    username=username,
                                    chat_group=group
                                )

                                if created:
                                    member_id.date_joined = ts
                                    member_id.save()

                                event, created = GroupEvent.objects.get_or_create(
                                    event_type=a,
                                    event_details=tail,
                                    initiated_by=member_id,
                                    chat_group=group, event_date=ts, file_upload=instance
                                )
                                if created:
                                    event.save()
            return group
        except Exception as e:
            pass

    def save_group_data(group_file, upload_details):
        with open(group_file, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f, delimiter=',')
            next(csv_reader)
            for row in csv_reader:
                messages = row[1].strip().replace('"', '')
                media = row[2].strip().strip().replace('"', '')
                emojis = row[3].strip().strip().replace('"', '')
                links = row[4].strip().strip().replace('"', '')
                upload_details.messages = messages
                upload_details.media = media
                upload_details.emojis = emojis
                upload_details.links = links
                upload_details.save()

    def save_message_file_link(message_file, upload_details):
        file = open(message_file, 'r')
        upload_details.message_file_link = file.name
        upload_details.save()
        file.close()
        return upload_details.message_file_link

    def save_events_file_link(events_file, upload_details):
        file = open(events_file, 'r')
        upload_details.events_file_link = file.name
        upload_details.save()
        file.close()
        return upload_details.events_file_link

    def save_members_file_link(members_file, upload_details):
        file = open(members_file, 'r')
        upload_details.members_file_link = file.name
        upload_details.save()
        file.close()
        return upload_details.members_file_link

    if chat_upload_id:
        print("instance created: ", chat_upload_id)
        chat_upload_instance = ChatUpload.objects.get(id=chat_upload_id)
        if chat_upload_instance:
            analysed_data = process_chat_file(chat_upload_instance.chat_txt_file.url)
            print("got analysed data")
            upload_file_details, up_created = ChatUploadDetails.objects.get_or_create(chat_upload=chat_upload_instance)
            if up_created:
                upload_file_details.events_file = save_events_file_link(
                    analysed_data.get('events'),
                    upload_file_details
                )
                upload_file_details.message_file = save_message_file_link(
                    analysed_data.get('messages'),
                    upload_file_details
                )
                upload_file_details.members_file = save_members_file_link(
                    analysed_data.get('users'),
                    upload_file_details
                )

                upload_file_details.most_popular_emojis = analysed_data.get('most_popular_emojis')

                upload_file_details.most_active_days = analysed_data.get('most_active_days')

                upload_file_details.most_active_members = analysed_data.get('most_active_members')

                attrition = analysed_data.get('attrition')

                upload_file_details.joined = attrition.get('Joined')

                upload_file_details.left = attrition.get('Left')

                upload_file_details.most_active_time = analysed_data.get('most_active_time')

                chat_group = save_events_details(analysed_data.get('events'), chat_upload_instance)

                upload_file_details.chat_group = chat_group

                upload_file_details.save()

                save_members_details(analysed_data.get('users'), chat_group, chat_upload_instance)

                save_messages_details(analysed_data.get('messages'), chat_group, chat_upload_instance)

                save_group_data(analysed_data.get('groups'), upload_file_details)

            if upload_file_details.chat_group != None:
                chat_upload_instance.is_analysed = UPLOAD_STATUS[1][1]
                chat_upload_instance.save()

            print("completed")


@periodic_task(run_every=(crontab(minute='*/1')), name="email_listener_task")
def email_listener_task():
    mail = Mail()
    mail.check_mail()
