import os
import re
import json
import sentry_sdk

from io import StringIO as IO

from django.db.models import Count
from django.db.utils import DataError
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.http.response import HttpResponseRedirect
from django.middleware import csrf
from django_registration.exceptions import ActivationError
from django_registration.backends.activation.views import RegistrationView, ActivationView
from django.shortcuts import render, redirect
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import resolve, reverse
from hashids import Hashids

from jinja2 import Template

from analyser.models import Personnel, WhatsAppGroup, WhatsAppChatFile, UserDailyStats, PERSONNEL_DESIGNATION_CHOICES
from analyser.common_tasks import Notification, Terminal
from analyser.analyser import Analyser
from analyser.serializers import PersonnelSerializer, WhatsAppGroupSerializer, WhatsAppChatFileSerializer, UserDailyStatsSerializer

# Import UserManagement 
from analyser.chat.UserManagement import UserManagement

from analyser.chat.MessageHistory import MessageHistory

terminal = Terminal()
sentry_sdk.init(settings.SENTRY_DSN)
manageUser = UserManagement()
messageHistory = MessageHistory()

cur_user_email = None
my_hashids = Hashids(min_length=5, salt=settings.SECRET_KEY)

User = get_user_model()

@login_required(login_url='/login')
def counselor_assignment(request):
    params = get_basic_info(request)
    params = {'s_date': ''}
    params['page_title'] = 'Counselor Assignment'
    params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']
    params['advisors'] = manageUser.getAllAdvisors()
    
    return render(request, 'dashboard/counselor_assignment.html', params)

@login_required(login_url='/login')
def advisor_assignment(request):
    params = get_basic_info(request)
    params = {'s_date': ''}
    params['page_title'] = 'Advisor Assignment'
    params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']
    params['advisors'] = manageUser.getAllAdvisors()
    params['managers'] = manageUser.getAllManagers()
    
    return render(request, 'dashboard/advisor_assignment.html', params)

@login_required(login_url='/login')
def assigned_counselors(request):
    params = get_basic_info(request)
    params = {'s_date': ''}
    params['page_title'] = 'Assigned Counselors'
    params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']
    params['cur_user'] = request.user

    
    data = manageUser.getCounselorsAssignedToAdvisor(request.user)
    params['assigned'] = data
    return render(request, 'dashboard/assigned_counselors.html', params)


@login_required(login_url='/login')
def whatsapp_groups_ba(request):
    params = get_basic_info(request)
    params = {'s_date': ''}
    params['page_title'] = 'WhatsApp Groups'
    params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']
    params['cur_user'] = request.user

    
    analyser = Analyser()
    # get all groups belonging to Business Analyst
    params['data'] = analyser.fetch_ba_groups_info(request.user)
    return render(request, 'dashboard/whatsapp_groups_ba.html', params)

def whatsapp_groups_bc(request):
    params = get_basic_info(request)
    params = {'s_date': ''}
    params['page_title'] = 'WhatsApp Groups'
    params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']
    params['cur_user'] = request.user

    
    analyser = Analyser()
    # get all groups belonging to Business Analyst
    params['data'] = analyser.fetch_bc_groups_info(request.user)
 
    return render(request, 'dashboard/whatsapp_groups_bc.html', params)

@login_required(login_url='/login')
def assigned_advisors(request):
    params = get_basic_info(request)
    params = {'s_date': ''}
    params['page_title'] = 'Assigned Counselors'
    params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']
    params['cur_user'] = request.user

    
    data = manageUser.getAdvisorsAssignedToManager(request.user)
    params['assigned'] = data
    return render(request, 'dashboard/assigned_advisors.html', params)

@login_required(login_url='/login')
def ajax_search_user_by_role(request):
    data = manageUser.searchPersonnelByRole(request.POST.get('keyword'), request.POST.get('role'))
    return JsonResponse(data, status=200, safe=False)

@login_required(login_url='/login')
def ajax_counselors_assigned_to_advisor(request):
    pk_id = my_hashids.decode(request.POST.get('advisor_id'))[0]
    user = User.objects.filter(id=pk_id).get()
    
    data = manageUser.getCounselorsAssignedToAdvisor(user)
    return JsonResponse(data, status=200, safe=False)

@login_required(login_url='/login')
def ajax_advisors_assigned_to_manager(request):
    pk_id = my_hashids.decode(request.POST.get('manager_id'))[0]
    user = User.objects.filter(id=pk_id).get()
    
    data = manageUser.getAdvisorsAssignedToManager(user)
    return JsonResponse(data, status=200, safe=False)

@login_required(login_url='/login')
def ajax_assign_counselor_to_advisor(request):
    pk_id_advisor = my_hashids.decode(request.POST.get('advisor_id'))[0]
    pk_id_counselor = my_hashids.decode(request.POST.get('counselor_id'))[0]

    advisor = User.objects.filter(id=pk_id_advisor).get()
    counselor = User.objects.filter(id=pk_id_counselor).get()

    data = manageUser.assignCounselorToAdvisor(counselor, advisor)
    return JsonResponse(data, status=200, safe=False)

@login_required(login_url='/login')
def ajax_assign_counselor_to_group(request):
    pk_id_group = my_hashids.decode(request.POST.get('group_id'))[0]
    pk_id_counselor = my_hashids.decode(request.POST.get('counselor_id'))[0]

    group = WhatsAppGroup.objects.filter(id=pk_id_group).get()
    counselor = User.objects.filter(id=pk_id_counselor).get()

    data = manageUser.assignCounselorToGroup(counselor, group)
    return JsonResponse(data, status=200, safe=False)

@login_required(login_url='/login')
def ajax_assign_advisor_to_manager(request):
    pk_id_manager = my_hashids.decode(request.POST.get('manager_id'))[0]
    pk_id_advisor = my_hashids.decode(request.POST.get('advisor_id'))[0]

    advisor = User.objects.filter(id=pk_id_advisor).get()
    manager = User.objects.filter(id=pk_id_manager).get()

    data = manageUser.assignAdvisorToManager(manager, advisor)
    return JsonResponse(data, status=200, safe=False)   

@login_required(login_url='/login')
def ajax_drop_counselor_assigned_to_advisor(request):
    pk_id_advisor = my_hashids.decode(request.POST.get('advisor_id'))[0]
    pk_id_counselor = my_hashids.decode(request.POST.get('counselor_id'))[0]

    advisor = User.objects.filter(id=pk_id_advisor).get()
    counselor = User.objects.filter(id=pk_id_counselor).get()

    data = manageUser.dropCounselorAssignedToAdvisor(counselor, advisor)
    return JsonResponse(data, status=200, safe=False)

@login_required(login_url='/login')
def ajax_drop_advisor_assigned_to_manager(request):
    pk_id_advisor = my_hashids.decode(request.POST.get('advisor_id'))[0]
    pk_id_manager = my_hashids.decode(request.POST.get('manager_id'))[0]

    advisor = User.objects.filter(id=pk_id_advisor).get()
    manager = User.objects.filter(id=pk_id_manager).get()

    data = manageUser.dropAdvisorAssignedToManager(manager, advisor)
    return JsonResponse(data, status=200, safe=False)


def get_basic_info(request):
    csrf_token = get_or_create_csrf_token(request)
    params = {'s_date': ''}

    global cur_user_email
    if request.session.session_key is not None:
        # update the session details
        cur_user = get_user_details(request)
        
        request.session['cu_designation'] = cur_user.get_designation_display()
        request.session['cu_designation_id'] = cur_user.designation
        request.session['cu_last_name'] = cur_user.last_name
        request.session['cu_first_name'] = cur_user.first_name
        request.session['cu_email'] = cur_user.email
        request.session['cu_issuperuser'] = cur_user.is_superuser
        if cur_user.is_superuser:
            request.session['cu_designation'] = 'Super Administrator'
        cur_user_email = cur_user.email

    elif request.session.get('cu_email') is not None:
        cur_user_email = request.session['cu_email']
    else:
        cur_user_email = None

    determine_user_links(request)
    
    return params


def get_or_create_csrf_token(request):
    token = request.META.get('CSRF_COOKIE', None)
    
    if token is None:
        token = csrf.get_token(request)
        request.META['CSRF_COOKIE'] = token

    request.META['CSRF_COOKIE_USED'] = True
    return token

@login_required(login_url='/login')
def get_user_details(request):
    # get the details of the logged in user
    # email = user.get_username()
    try:
        personnel = Personnel.objects.get(id=request.user.id)

        return personnel
    except Personnel.DoesNotExist as e:
        sentry_sdk.capture_exception(e)
        if settings.DEBUG: terminal.tprint("%s: A user who is not vetted is trying to log in. Kick them out." % str(e), 'fail')
        return None


def determine_user_links(request):
    nav_links = [{
        'type': 'link', 'href': '#', 'icon': '<i class="fi fi-orbit"></i>', 'link_title': 'Reports', 'allowed_users': ['data_manager', 'system_admin'], 
        'items': [
            {'type': 'link', 'icon': '<i class="fi fi-users"></i>', 'href': '/groups', 'link_title': 'WhatsApp Groups', 'allowed_users': ['data_manager', 'system_admin'] },
            {'type': 'link', 'icon': '<i class="fi fi-users"></i>', 'href': '/engaged_users', 'link_title': 'Enagaged Users', 'allowed_users': ['data_manager', 'system_admin'] }
        ]},
        {
        'type': 'link', 'href': '#', 'icon': '<i class="fi fi-users"></i>', 'link_title': 'Manage', 'allowed_users': ['data_manager', 'system_admin'], 
        'items': [
            {'type': 'link', 'icon': '<i class="fi fi-users"></i>', 'href': '/counselor_assignment', 'link_title': 'Counselor Assignment', 'allowed_users': ['data_manager', 'system_admin'] },
            {'type': 'link', 'icon': '<i class="fi fi-users"></i>', 'href': '/advisor_assignment', 'link_title': 'Advisor Assignment', 'allowed_users': ['data_manager', 'system_admin'] }
        ]},
        {'type': 'link', 'href': 'https://drive.google.com/drive/u/2/folders/1LPyG58hCMnMd6m9touobHPUXCPGfmD6a', 'icon': '<i class="fi fi-layers"></i>', 'link_title': 'Upload', 'allowed_users': ['business_advisor', 'business_counselor', 'program_manager']}, 
        
        {'type': 'link', 'href': '/assigned_counselors', 'icon': '<i class="fi fi-users"></i>', 'link_title': 'Assigned Counselors', 'allowed_users': ['business_advisor']}, 
        {'type': 'link', 'href': '/whatsapp_groups_ba', 'icon': '<i class="fi fi-users"></i>', 'link_title': 'WhatsApp Groups', 'allowed_users': ['business_advisor']}, 
        {'type': 'link', 'href': '/whatsapp_groups_bc', 'icon': '<i class="fi fi-users"></i>', 'link_title': 'WhatsApp Groups', 'allowed_users': ['business_counselor']}, 

        {'type': 'link', 'href': '/assigned_advisors', 'icon': '<i class="fi fi-users"></i>', 'link_title': 'Assigned Advisors', 'allowed_users': ['program_manager']}, 
        
        {
        'type': 'link', 'href': '#', 'icon': '<i class="fi fi-layers-middle"></i>', 'link_title': 'Admin Section', 'allowed_users': ['data_manager', 'system_admin'], 
        'items': [
            {'type': 'link', 'icon': '<i class="fi fi-users"></i>', 'href': '/users', 'link_title': 'System Users', 'allowed_users': ['data_manager', 'system_admin'] },
            {'type': 'link', 'icon': '<i class="fi fi-users"></i>', 'href': '/files_repo', 'link_title': 'Exported Files', 'allowed_users': ['data_manager', 'system_admin'] },
        ]
    }]

    allowed_links = []
    for link in nav_links:
        if link['allowed_users'] == 'all' or request.session['cu_issuperuser'] or request.session['cu_designation_id'] in link['allowed_users']:

            # check if the active path is in the items
            if 'items' in link:
                is_cur_active = False
                for i in link['items']:
                    if i['allowed_users'] == 'all' or request.session['cu_issuperuser'] or request.session['cu_designation_id'] in i['allowed_users']:
                        if i['href'] == request.path_info:
                            i['is_active'] = True
                            is_cur_active = True
                        else: i['is_active'] = False

                link['is_active'] = is_cur_active

            else:
                link['is_active'] = True if link['href'] == request.path_info else False

            allowed_links.append(link)

    request.session['nav_links'] = allowed_links



#FIXME delete this after testing chats
@login_required(login_url='/login')
def getchats(request):
    params = get_basic_info(request)
    params = {'s_date': ''}
    params['page_title'] = 'Assigned Counselors'
    params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']
    params['cur_user'] = request.user

    data = manageUser.getCounselorsAssignedToAdvisor(request.user)
    date = '2021-09-07'
    group_id = 1

    messages = messageHistory.getMessageLogByDate(date,group_id)
    params['assigned'] = data
    params['messages'] = messages
    return render(request, 'dashboard/chats.html', params)

#FIXME delete this after testing chats
@login_required(login_url='/login')
def getwordcloud(request):
    params = get_basic_info(request)
    params = {'s_date': ''}
    params['page_title'] = 'Assigned Counselors'
    params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']
    params['cur_user'] = request.user

    data = manageUser.getCounselorsAssignedToAdvisor(request.user)
    date = '2021-09-07'
    group_id = 1

    messages = messageHistory.getMessageLogByDate(date,group_id)
    params['assigned'] = data
    params['messages'] = messages
    return render(request, 'dashboard/cloud.html', params)

@login_required(login_url='/login')
def searchGroupChatByDate(request):
    #group_id=int(my_hashids.decode(request.POST.get('group_id'))[0])

    data = messageHistory.getMessageLogByDate(request.POST.get('date'), request.POST.get('group_id'))
    return JsonResponse(data, status=200, safe=False)