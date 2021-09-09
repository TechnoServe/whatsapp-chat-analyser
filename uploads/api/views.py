import datetime

from django.shortcuts import get_object_or_404
# Create your views here.
from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from uploads.api.serializer import ChatUploadSerializer, ChatUploadByIDSerializer, ChatUploadsListSerializer, \
    ChatUploadDetailsSerializer
from uploads.models import ChatUpload, ChatUploadDetails
from uploads.tasks import analyse_export_chat_task


class ChatUploadsViewSet(viewsets.ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = ChatUpload.objects.all()
    serializer_class = ChatUploadSerializer

    def get_queryset(self):
        return self.queryset.all()

    # list uploaded files
    def list(self, request):
        query_set = ChatUploadDetails.objects.all()
        serializer = ChatUploadsListSerializer(query_set, many=True)
        return Response(serializer.data)

    # create a chat upload
    def create(self, request, *args, **kwargs):
        uploaded_by = request.user.pk
        date_uploaded = datetime.datetime.now()
        file = request.FILES.get('chat_txt_file')

        filename = request.FILES.get('chat_txt_file').name
        data = {'date_uploaded': date_uploaded, 'chat_file_name': filename, 'chat_txt_file': file,
                'uploaded_by': uploaded_by}

        serializer = ChatUploadSerializer(data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            celery_task_result = analyse_export_chat_task.delay(serializer.data.get('id'))
            print("celery_task_result: ", celery_task_result)
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        data.pop('chat_txt_file')
        return Response(data={"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    # view chat upload by id
    def retrieve(self, request, pk=None):
        query_set = self.get_queryset()
        data = get_object_or_404(query_set, pk=pk)
        serializer = ChatUploadByIDSerializer(data)
        return Response(serializer.data)
