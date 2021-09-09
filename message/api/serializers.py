from rest_framework import serializers

from members.api.serializer import GroupMemberSerializer
from message.models import GroupMessage


class ChatGroupMessageSerializer(serializers.ModelSerializer):
    sender = GroupMemberSerializer(required=False)

    class Meta:
        model = GroupMessage
        fields = '__all__'
