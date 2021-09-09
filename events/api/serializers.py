from rest_framework import serializers

from events.models import GroupEvent
from members.api.serializer import GroupMemberSerializer


class ChatGroupEventSerializer(serializers.ModelSerializer):
    initiated_by = GroupMemberSerializer(required=False)

    class Meta:
        model = GroupEvent
        fields = '__all__'
