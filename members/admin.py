from django.contrib import admin

# Register your models here.
from members.models import GroupMember

admin.site.register(GroupMember)