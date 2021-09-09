from django.db import models


# Create your models here.


class GroupMember(models.Model):
    # pass

    username = models.CharField(max_length=255, null=False, verbose_name='group_member_username')
    messages = models.IntegerField(null=True)
    words = models.IntegerField(null=True)
    emojis = models.TextField(null=True)
    media = models.TextField(null=True)
    links = models.TextField(null=True)
    top_emojis = models.TextField(null=True)
    top_words = models.TextField(null=True)
    top_links = models.TextField(null=True)
    date_joined = models.DateTimeField(null=True)
    is_group_admin = models.BooleanField(null=True, default=False)
    upload_id = models.ForeignKey('uploads.ChatUpload', on_delete=models.DO_NOTHING, null=True,
                                  related_name='member_upload_list')
    chat_group = models.ForeignKey('chatgroup.ChatGroup', on_delete=models.DO_NOTHING, null=True,
                                   related_name='chat_group_members')

    def __str__(self):
        return self.username
