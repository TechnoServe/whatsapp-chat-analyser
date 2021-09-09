'''
Router
'''
from django.urls import path, include
from rest_framework import routers

from chatgroup.api.views import ChatGroupViewSet
from events.api.views import GroupEventsViewSet
from members.api.views import GroupMemberViewSet
from uploads.api.views import ChatUploadsViewSet
from users import urls as users_urls

router = routers.DefaultRouter()
router.register(r'chatgroups', ChatGroupViewSet, basename="chatgroup")
router.register(r'uploads', ChatUploadsViewSet, basename="upload_file")
router.register(r'members', GroupMemberViewSet, basename="members")
router.register(r'events', GroupEventsViewSet, basename="events")

url_patterns = [
    path('api/v1/', include(router.urls)),

]

