# Create your views here.
import json

from django.contrib.auth import authenticate
from django.core.exceptions import MultipleObjectsReturned
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters
from oauth2_provider.models import get_access_token_model
from oauth2_provider.signals import app_authorized
from oauth2_provider.views import TokenView
from rest_framework import status
from rest_framework.generics import UpdateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from users.api.serializer import LoginSerializer, UserSerializer
from users.models import User
from utils.common import save_headers


class CurrentUserView(APIView):
    """
    Current user
    """

    @save_headers
    def get(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data)

@method_decorator(csrf_exempt, name="dispatch")
class CheckUserView(ListAPIView):
    """
    Check user exists
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request, username, *args, **kwargs):
        """
        Pass in the username, ignore any headers provided
        """
        try:
            # Try email
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'Error': 'Cannot find user'},
                            status=status.HTTP_400_BAD_REQUEST)

        data = {
            'email': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        return Response(data, status=status.HTTP_200_OK)

class LoginView(UpdateAPIView):
    permission_classes = []
    authentication_classes = []
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            username = serializer.data.get("username")
            password = serializer.data.get("password")

            user = authenticate(username=username, password=password)
            if user:
                return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class CustomTokenView(TokenView):

    @method_decorator(sensitive_post_parameters("password"))
    def post(self, request, *args, **kwargs):
        url, headers, body, status = self.create_token_response(request)
        if status == 200:
            body = json.loads(body)
            access_token = body.get("access_token")
            if access_token is not None:
                token = get_access_token_model().objects.get(
                    token=access_token)
                app_authorized.send(
                    sender=self, request=request,
                    token=token)
                # adding user permissions to login endpoint
                body['permissions'] = [
                    item for item in token.user.get_all_permissions()]

                body = json.dumps(body)
        response = HttpResponse(content=body, status=status)
        for k, v in headers.items():
            response[k] = v
        return response
