'''
users urls
'''

import oauth2_provider.views as oauth2_views
from django.conf import settings
from django.conf.urls import url
from django.urls import path, include

from users.api.views import LoginView, CustomTokenView, CheckUserView, CurrentUserView

oauth2_endpoint_views = [
    url(r'^authorize/$', oauth2_views.AuthorizationView.as_view(), name="authorize"),
    url(r'^token/$', CustomTokenView.as_view(), name="token"),
    url(r'^revoke-token/$', oauth2_views.RevokeTokenView.as_view(), name="revoke-token"),
]

if settings.DEBUG:
    # OAuth2 Application Management endpoints
    oauth2_endpoint_views += [
        url(r'^applications/$', oauth2_views.ApplicationList.as_view(), name="list"),
        url(r'^applications/register/$',
            oauth2_views.ApplicationRegistration.as_view(), name="register"),
        url(r'^applications/(?P<pk>\d+)/$',
            oauth2_views.ApplicationDetail.as_view(), name="detail"),
        url(r'^applications/(?P<pk>\d+)/delete/$',
            oauth2_views.ApplicationDelete.as_view(), name="delete"),
        url(r'^applications/(?P<pk>\d+)/update/$',
            oauth2_views.ApplicationUpdate.as_view(), name="update"),
    ]

    # OAuth2 Token Management endpoints
    oauth2_endpoint_views += [
        url(
            r'^authorized-tokens/$',
            oauth2_views.AuthorizedTokensListView.as_view(),
            name="authorized-token-list"
        ),
        url(
            r'^authorized-tokens/(?P<pk>\d+)/delete/$',
            oauth2_views.AuthorizedTokenDeleteView.as_view(),
            name="authorized-token-delete"
        ),
    ]

urlpatterns = [
    path(
        r'api/v1/users/check-user/<username>/',
        CheckUserView.as_view(),
        name='check_user'
    ),
    path(
        r'api/v1/users/login-user/',
        LoginView.as_view(),
        name='login_user'
    ),
    # deprecate this endpoint
    url(r'^api/v1/users/current-user', CurrentUserView.as_view()),
    url(r'^api/v1/users/current-user/', CurrentUserView.as_view()),
    # add 0AUTH2 endpoints
    url(r'^api/v1/oauth/', include((oauth2_endpoint_views,
                                    'oauth2_provider'), namespace='oauth2_provider')),
]