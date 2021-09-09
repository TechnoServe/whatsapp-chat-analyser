'''
serialize uploads models
'''

from rest_framework import serializers

from chatgroup.api.serializer import ChatGroupSerializer
from events.api.serializers import ChatGroupEventSerializer
from members.api.serializer import GroupMemberSerializer
from message.api.serializers import ChatGroupMessageSerializer
from uploads.models import ChatUpload, ChatUploadDetails, UPLOAD_STATUS
from users.api.serializer import UserSerializer


class ChatUploadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    def create(self, validated_data):
        date_data = validated_data.pop('date_uploaded')
        file_data = validated_data.pop('chat_txt_file')
        chat, created = ChatUpload.objects.get_or_create(
            uploaded_by=validated_data.get('uploaded_by'),
            chat_file_name=validated_data.get('chat_file_name')
        )
        if created:
            chat.chat_txt_file = file_data
            chat.date_uploaded = date_data
            chat.is_analysed = UPLOAD_STATUS[2][1]
            chat.save()

        return chat

    class Meta:
        model = ChatUpload
        fields = ['id', 'uploaded_by', 'chat_file_name', 'chat_txt_file', 'date_uploaded', 'is_analysed']


class ChatUploadDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatUploadDetails
        fields = '__all__'


class ChatUploadByIDSerializer(serializers.ModelSerializer):
    chat_file_details = ChatUploadDetailsSerializer()
    member_upload_list = GroupMemberSerializer(many=True)
    message_upload_list = ChatGroupMessageSerializer(many=True)
    events_upload_list = ChatGroupEventSerializer(many=True)
    uploaded_by = UserSerializer()

    class Meta:
        model = ChatUpload
        fields = [
            'id',
            'chat_file_name', 'chat_txt_file', 'uploaded_by', 'date_uploaded', 'is_analysed',
            'chat_file_details', 'member_upload_list', 'message_upload_list', 'events_upload_list'
        ]


# display chat upload including serialized user
class ChatUploadListSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(required=False)

    class Meta:
        model = ChatUpload
        fields = ['id', 'uploaded_by', 'chat_file_name', 'chat_txt_file', 'date_uploaded', 'is_analysed']


# display main chat file details
class ChatUploadsListSerializer(serializers.ModelSerializer):
    chat_upload = ChatUploadListSerializer(required=False)
    chat_group = ChatGroupSerializer(required=False)

    class Meta:
        model = ChatUploadDetails
        fields = ['id', 'chat_upload', 'chat_group', 'messages', 'media', 'emojis', 'links']
