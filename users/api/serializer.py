'''
user serializer
'''
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from users.models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class UserSerializer(serializers.ModelSerializer):
    # groups = serializers.SerializerMethodField()
    # access_token = serializers.SerializerMethodField()
    # permissions = serializers.SerializerMethodField()
    # name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'is_active',
        )


    def get_access_token(self, user):
        access_token = 'not-a-login-user'
        try:
            access_token = Token.objects.get(user=user).key
        except Exception:
            pass

        return access_token

    def get_permissions(self, user):
        return [item for item in user.get_all_permissions()]

    def get_groups(self, user):
        return [item.id for item in user.groups.all()]

    def create(self, validated_data):
        validated_data['username'] = validated_data['email']
        return super(UserSerializer, self).create(validated_data)