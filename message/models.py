from django.db import models
# Create your models here.
from gdstorage.storage import GoogleDriveStorage

from members.models import GroupMember




class GroupMessage(models.Model):
    # pass

    sender = models.ForeignKey('members.GroupMember', null=False, on_delete=models.DO_NOTHING, related_name='sender')
    created = models.DateTimeField(null=False)
    message_text = models.TextField(null=False, default="dummy text")
    upload_id = models.ForeignKey('uploads.ChatUpload', on_delete=models.DO_NOTHING, null=True,
                                  related_name='message_upload_list')
    chat_group = models.ForeignKey('chatgroup.ChatGroup', related_name='chat_group_messages',  null=False,  on_delete=models.DO_NOTHING)

