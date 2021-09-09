# Create your views here.
from rest_framework import viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from events.api.serializers import ChatGroupEventSerializer
from events.models import GroupEvent


class GroupEventsViewSet(viewsets.ModelViewSet):
    queryset = GroupEvent.objects.all()
    serializer_class = ChatGroupEventSerializer

    def list(self, request):
        queryset = GroupEvent.objects.all()
        serializer = ChatGroupEventSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = GroupEvent.objects.all()
        data = get_object_or_404(queryset, pk=pk)
        serializer = ChatGroupEventSerializer(data)
        return Response(serializer.data)
