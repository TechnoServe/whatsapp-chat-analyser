from rest_framework import serializers

from members.models import GroupMember


class GroupMemberSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        return GroupMember(**validated_data)

    class Meta:
        model = GroupMember
        fields='__all__'

