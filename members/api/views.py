# Create your views here.
import datetime

from rest_framework import viewsets, status
from rest_framework.response import Response

from members.api.serializer import GroupMemberSerializer
from members.models import GroupMember


class GroupMemberViewSet(viewsets.ViewSet):
    """
        A viewset that provides the standard actions
        """
    queryset = GroupMember.objects.all()
    serializer_class = GroupMemberSerializer

    def get_queryset(self):
        return self.queryset.all()

    def list(self, request):
        query_set = self.get_queryset()
        serializer = GroupMemberSerializer(query_set, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def create(self, request, *args, **kwargs):
        username = request.user.pk
        date_joined = datetime.datetime.now()
        extra_data = dict(username=username, date_joined=date_joined)
        request_data = dict(request.data)
        data = extra_data.update(request_data)
        serializer = GroupMemberSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(status=status.HTTP_201_CREATED, data=serializer.data)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        pass

    def update(self, request, pk=None):
        pass

    def partial_update(self, request, pk=None):
        pass

    def destroy(self, request, pk=None):
        pass
