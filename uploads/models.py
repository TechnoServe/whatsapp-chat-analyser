from django.db import models
from django.db.models import Model
from gdstorage.storage import GoogleDriveStorage

from chatgroup.models import ChatGroup
from events.models import GroupEvent
from members.models import GroupMember
from message.models import GroupMessage
from users.models import User

gd_storage = GoogleDriveStorage()

NO = 'NO'
YES = 'YES'
ANALYSING = 'ANALYSING'
UPLOAD_STATUS = [(NO, 'No'), (YES, 'Yes'), (ANALYSING, 'Analysing')]

class ChatUpload(models.Model):
    chat_file_name = models.CharField(max_length=1000, blank=True)
    chat_txt_file = models.FileField(upload_to='mspark-test-folder', verbose_name='chat_txt_file', storage=gd_storage, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='file_uploader', null=False)
    date_uploaded = models.DateTimeField(null=True)
    is_analysed = models.CharField(null=False, default=NO, choices=UPLOAD_STATUS, max_length=255)

    def __str__(self):
        return self.chat_file_name


class ChatUploadDetails(models.Model):
    chat_upload = models.OneToOneField(ChatUpload, on_delete=models.DO_NOTHING, related_name='chat_file_details',
                                    null=False)
    chat_group = models.ForeignKey(ChatGroup, on_delete=models.DO_NOTHING, related_name='chat_upload_group', null=True,
                                   blank=True)
    members_file_link = models.FileField(
        storage=gd_storage, verbose_name='members_file_link',
        upload_to="mspark-test-folder", null=True)
    events_file_link = models.FileField(
        storage=gd_storage, verbose_name='events_file_link',
        upload_to="mspark-test-folder", null=True)
    messages_file_link = models.FileField(
        storage=gd_storage, verbose_name='messages_file_link',
        upload_to="mspark-test-folder",
        null=True)
    most_popular_emojis = models.CharField(max_length=1000, null=True)
    most_active_days = models.CharField(max_length=1000, null=True)
    most_active_members = models.CharField(
        max_length=1000, null=True)
    joined = models.CharField(max_length=1000, null=True)
    left = models.CharField(max_length=1000, null=True)
    most_active_time = models.CharField(max_length=1000, null=True)
    messages = models.IntegerField(default=0, null=True)
    media = models.IntegerField(default=0, null=True)
    emojis = models.IntegerField(default=0, null=True)
    links = models.IntegerField(default=0, null=True)

    def __str__(self):
        return "{}".format(self.id)
