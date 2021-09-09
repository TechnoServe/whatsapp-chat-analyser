'''
forms to upload text files
'''
from django import forms

from uploads.models import ChatUpload


class ExportFileUploadForm(forms.Form):
    class Meta:
        model=ChatUpload
        fields=['file_url', 'file_name', 'chat_group']