import datetime

from rest_framework import viewsets, status
# Create your views here.
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from chatgroup.api.serializer import ChatGroupSerializer
from chatgroup.models import ChatGroup


class ChatGroupViewSet(viewsets.ViewSet):
    queryset = ChatGroup.objects.all()
    serializer_class = ChatGroupSerializer


    def list(self, request):
        queryset = self.queryset.all()
        serializer = ChatGroupSerializer(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        queryset = self.queryset.all()
        data = get_object_or_404(queryset, pk=pk)
        serializer = ChatGroupSerializer(data)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        data = request.data
        data['date_created'] = datetime.datetime.now()
        data['created_by'] = request.user
        print("data: ", data)
        serializer = ChatGroupSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.create(validated_data=data)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)
