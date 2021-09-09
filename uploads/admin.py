from django.contrib import admin

# Register your models here.
# from uploads.models import ChatUpload
from uploads.models import ChatUpload, ChatUploadDetails

admin.site.register(ChatUpload)
admin.site.register(ChatUploadDetails)