from django.apps import apps
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework import routers

from rest_framework.authtoken import views as auth_views
from analyser import views


urlpatterns = [
    re_path(r'^admin/', admin.site.urls, name='admin'),
    re_path(r'^$', views.index, name='home'),
    re_path(r'^signin$', views.signin, name='signin'),

    re_path(r'^login$', views.login_page, name='login_page'),
    re_path(r'^logout/$', views.user_logout, name='user_logout'),
    
    re_path(r'^(?P<d_type>add_user)/$', views.add_objects, name='add_objects'),
    re_path(r'^(?P<d_type>edit_user)/$', views.edit_objects, name='edit_objects'),
    re_path(r'^(?P<d_type>delete_user)/$', views.delete_objects, name='delete_objects'),

    re_path(r'^activate_user|deactivate_user/$', views.manage_objects, name='manage_objects'),
    re_path(r'^new_user_password/?(?P<uid>[0-9A-Za-z_\-]+)?/?(?P<token>[0-9A-Za-z\-]+)?$', views.new_user_password, name='new_user_password'),
    re_path(r'^recover_password$', views.recover_password, name='recover_password'),
    re_path(r'^activate_new_user/(?P<user>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z_\:\-]{1,80})$', views.activate_user, name='activate'),
    re_path(r'^save_user_password$', views.save_user_password, name='save_user_password'),

    re_path(r'^data/(?P<d_type>users|exported_files|search|engaged_users)(/(?P<filter_>.+))?$', views.get_ajax_data, name='ajax_data'),

    re_path(r'^dashboard.pm$', views.dashboardPM, name='dashboard.pm'),
    re_path(r'^dashboard.ba$', views.dashboardBA, name='dashboard.ba'),
    re_path(r'^dashboard.bc$', views.dashboardBC, name='dashboard.bc'),
    re_path(r'^dashboard$', views.dashboard, name='dashboard'),
    re_path(r'^groups$', views.list_whatsapp_chats, name='list_whatsapp_chats'),
    re_path(r'^engaged_users$', views.list_whatsapp_users, name='list_whatsapp_users'),
    re_path(r'^files_repo$', views.list_exported_files, name='list_exported_files'),
    re_path(r'^group_stats/(?P<uid>[0-9A-Za-z_\-]+)$', views.show_group_stats, name='show_group_stats'),
    re_path(r'^user_stats/(?P<gid>[0-9A-Za-z_\-]+)/(?P<user_>.+)$', views.show_user_stats, name='show_user_stats'),

    re_path(r'^group_stats$', views.dashboard, name='dashboard'),
    re_path(r'^user_stats$', views.dashboard, name='dashboard'),
    re_path(r'^process_new_chats$', views.process_new_chats, name='process_new_chats'),

    re_path(r'^validate_input', views.validate_objects, name='validate_objects'),
    re_path(r'^users$', views.users, name='users'),

    re_path(r'^resend_activation_email$', views.resend_activation_email, name='resend_activation_email'),

    re_path(r'^counselor_assignment$', views.counselor_assignment, name='counselor_assignment'),
    re_path(r'^ajax_search_user_by_role$', views.ajax_search_user_by_role, name='ajax_search_user_by_role'),
    re_path(r'^ajax_counselors_assigned_to_advisor$', views.ajax_counselors_assigned_to_advisor, name='ajax_counselors_assigned_to_advisor'),
    re_path(r'^ajax_assign_counselor_to_advisor$', views.ajax_assign_counselor_to_advisor, name='ajax_assign_counselor_to_advisor'),
    re_path(r'^ajax_drop_counselor_assigned_to_advisor$', views.ajax_drop_counselor_assigned_to_advisor, name='ajax_drop_counselor_assigned_to_advisor'),

    # Advisor assignment
    re_path(r'^advisor_assignment$', views.advisor_assignment, name='advisor_assignment'),
    re_path(r'^ajax_advisors_assigned_to_manager$', views.ajax_advisors_assigned_to_manager, name='ajax_advisors_assigned_to_manager'),
    re_path(r'^ajax_assign_advisor_to_manager$', views.ajax_assign_advisor_to_manager, name='ajax_assign_advisor_to_manager'),
    re_path(r'^ajax_drop_advisor_assigned_to_manager$', views.ajax_drop_advisor_assigned_to_manager, name='ajax_drop_advisor_assigned_to_manager'),
    

    re_path(r'^assigned_counselors$', views.assigned_counselors, name='assigned_counselors'),
    re_path(r'^chats$', views.getchats, name='assigned_counselors'),
    re_path(r'^assigned_advisors$', views.assigned_advisors, name='assigned_advisors'),



    
    

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


if settings.DEBUG:
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIAFILES_DIRS}),
    ]
