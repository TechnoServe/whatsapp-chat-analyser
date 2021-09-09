"""mspark_whatsapp_analyzer URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sites.models import Site
from django.urls import path, include
from rest_framework.documentation import include_docs_urls
from mspark_whatsapp_analyzer.router import url_patterns as router_patterns
from uploads import urls as uploads_url
from chatgroup import urls as chatgroup_url
from users import urls as users_urls

try:
    site_header = Site.objects.get_current().name
except Exception:
    site_header = settings.SITE_HEADER

admin.site.site_header = site_header



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(users_urls)),
    url(r'', include_docs_urls(title="{} API Docs".format(site_header), public=False)),
    path('api/', include('rest_framework.urls', namespace='rest_framework')),

]
admin.site.enable_nav_sidebar = False
urlpatterns = urlpatterns + router_patterns
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)