from django.contrib import admin

# Register your models here.
from message.models import GroupMessage

admin.site.register(GroupMessage)