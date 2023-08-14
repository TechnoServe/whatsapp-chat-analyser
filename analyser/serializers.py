from django.conf import settings

from .models import (
    Personnel,
    WhatsAppGroup,
    WhatsAppChatFile,
    GroupDailyStats,
    UserDailyStats,
    AdvisorManagerAssignment,
    CounselorAdvisorAssignment,
    MessageLog,
)
from rest_framework import serializers
from hashids import Hashids

my_hashids = Hashids(min_length=5, salt=settings.SECRET_KEY)


class BaseSerializer(serializers.ModelSerializer):
    pk_id = serializers.SerializerMethodField()

    def get_pk_id(self, obj):
        try:
            return my_hashids.encode(obj.id)
        except AttributeError:
            return my_hashids.encode(obj["id"])


class BaseSerializerDict(serializers.ModelSerializer):
    pk_id = serializers.SerializerMethodField()

    def get_pk_id(self, obj):
        return my_hashids.encode(obj["id"])


class PersonnelSerializer(BaseSerializer):
    class Meta:
        model = Personnel
        fields = [
            "pk_id",
            "last_login",
            "is_superuser",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "designation",
            "nickname",
            "tel",
        ]
        depth = 1


class WhatsAppGroupSerializer(BaseSerializer):
    class Meta:
        model = WhatsAppGroup
        fields = ("pk_id", "group_name", "datetime_created", "created_by")
        depth = 1


class WhatsAppChatFileSerializer(BaseSerializer):
    group = WhatsAppGroupSerializer()

    class Meta:
        model = WhatsAppChatFile
        fields = (
            "pk_id",
            "google_id",
            "group",
            "web_content_link",
            "title",
            "datetime_created",
            "filesize",
            "status",
            "comments",
            "email",
        )
        depth = 1


class GroupDailyStatsSerializer(BaseSerializer):
    group = WhatsAppGroupSerializer()
    chat_file = WhatsAppChatFileSerializer()

    class Meta:
        model = GroupDailyStats
        fields = (
            "pk_id",
            "stats_date",
            "new_users",
            "left_users",
            "most_active_hr",
            "emojis",
            "filesize",
            "no_messages",
            "no_images",
            "no_links",
        )
        depth = 1


class UserDailyStatsSerializer(BaseSerializer):
    group = WhatsAppGroupSerializer()
    chat_file = WhatsAppChatFileSerializer()

    class Meta:
        model = UserDailyStats
        fields = (
            "pk_id",
            "group",
            "chat_file",
            "name_phone",
            "stats_date",
            "most_active_hr",
            "emojis",
            "no_messages",
            "no_images",
            "no_links",
        )
        depth = 1


class CounselorAdvisorAssignmentSerializer(BaseSerializer):
    counselor = PersonnelSerializer()

    class Meta:
        model = CounselorAdvisorAssignment
        fields = ["advisor", "counselor"]


class AdvisorManagerAssignmentSerializer(BaseSerializer):
    advisor = PersonnelSerializer()

    class Meta:
        model = AdvisorManagerAssignment
        fields = ["advisor", "manager"]


class MessageLogSerializer(BaseSerializer):
    user = UserDailyStatsSerializer()

    class Meta:
        model = MessageLog
        fields = ["message", "datetime_sent", "user"]
