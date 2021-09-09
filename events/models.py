

from django.db import models
#
# GroupEvent models track attrition levels
from django.utils import timezone
from gdstorage.storage import GoogleDriveStorage

gd_storage = GoogleDriveStorage()
#
#
class GroupEvent(models.Model):

    event_type = models.TextField(null=False)
    event_details = models.TextField(null=False, default="")
    initiated_by = models.ForeignKey('members.GroupMember', on_delete=models.DO_NOTHING, related_name='event_initiator',
                                      null=False)
    file_upload = models.ForeignKey('uploads.ChatUpload', on_delete=models.DO_NOTHING, related_name='events_upload_list')
    event_date = models.DateTimeField(verbose_name='event_date')
    chat_group = models.ForeignKey('chatgroup.ChatGroup', related_name='chat_group_events', on_delete=models.DO_NOTHING)
