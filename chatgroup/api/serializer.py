'''

'''

from rest_framework import serializers

from chatgroup.models import ChatGroup
from members.api.serializer import GroupMemberSerializer


class ChatGroupSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    group_admin = GroupMemberSerializer(many=False, read_only=True)
    date_created = serializers.DateTimeField()

    #
    def create(self, validated_data):
        return ChatGroup.objects.create(**validated_data)

    class Meta:
        model = ChatGroup
        fields = '__all__'

