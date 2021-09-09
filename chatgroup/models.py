from django.utils import timezone

from django.db import models
# track group chats
from gdstorage.storage import GoogleDriveStorage

from events.models import GroupEvent
from members.models import GroupMember
from message.models import GroupMessage
from users.models import User

# Create your models here.
# from members.models import GroupMember
gd_storage = GoogleDriveStorage()


class ChatGroup(models.Model):

    name = models.TextField(null=False, unique=True, verbose_name='chat_group_name')
    date_created = models.DateTimeField(null=False)
    created_by = models.ForeignKey('users.User', default=1, on_delete=models.CASCADE, null=True, related_name='group_creator')

    def __str__(self):
        return self.name
