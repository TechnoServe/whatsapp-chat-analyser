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

terminal = Terminal()
sentry_sdk.init(settings.SENTRY_DSN)

cur_user_email = None
my_hashids = Hashids(min_length=5, salt=settings.SECRET_KEY)

User = get_user_model()


class CustomPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """Custom Password Token Generator Class."""
    def _make_hash_value(self, user, timestamp):
        # Include user email alongside user password to the generated token
        # as the user state object that might change after a password reset
        # to produce a token that invalidated.
        login_timestamp = '' if user.last_login is None\
            else user.last_login.replace(microsecond=0, tzinfo=None)
        return str(user.pk) + user.password + user.email +\
            str(login_timestamp) + str(timestamp)


default_token_generator = CustomPasswordResetTokenGenerator()


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


def validate_user_access(request, data_type):
    # determine whether the current user has rights to access current resources
    # data_collector
    access_rights = {
        'users': ['admins']
    }
    try:
        if request.session['cu_issuperuser'] or request.session['cu_designation_id'] == 'system_admin' or request.session['cu_designation_id'] == 'business_counselor' or request.session['cu_designation_id'] == 'business_advisor' or request.session['cu_designation_id'] == 'program_manager': return True
        if request.session['cu_designation_id'] in access_rights[data_type]: return True

        raise Exception('Sorry you dont have rights to access the current resource')
    except Exception: raise


def get_or_create_csrf_token(request):
    token = request.META.get('CSRF_COOKIE', None)
    
    if token is None:
        token = csrf.get_token(request)
        request.META['CSRF_COOKIE'] = token

    request.META['CSRF_COOKIE_USED'] = True
    return token


def determine_user_links(request):
    nav_links = [{
        'type': 'link', 'href': '#', 'icon': '<i class="fi fi-orbit"></i>', 'link_title': 'Reports', 'allowed_users': ['data_manager', 'system_admin'], 
        'items': [
            {'type': 'link', 'icon': '<i class="fi fi-users"></i>', 'href': '/groups', 'link_title': 'WhatsApp Groups', 'allowed_users': ['data_manager', 'system_admin'] },
            {'type': 'link', 'icon': '<i class="fi fi-users"></i>', 'href': '/engaged_users', 'link_title': 'Enagaged Users', 'allowed_users': ['data_manager', 'system_admin'] }
        ]},
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


def index(request):
    # current_site = get_current_site(request)
    params = {'site_name': settings.SITE_NAME}
    template = 'index.html'

    return render(request, template, params)


def signin(request):
    csrf_token = get_or_create_csrf_token(request)
    params = {'site_name': settings.SITE_NAME, 'csrf_token': csrf_token}
    template = 'signin.html'

    return render(request, template, params)


def login_page(request, *args, **kwargs):
    csrf_token = get_or_create_csrf_token(request)
    page_settings = {'page_title': "%s | Login Page" % settings.SITE_NAME, 'csrf_token': csrf_token}
    #terminal.tprint('###########################in authenticate', 'debug')
    try:
        # check if we have some username and password in kwargs
        if 'kwargs' in kwargs:
            # use the explicitly passed username and password over the form filled ones
            username = kwargs['kwargs']['user']['username']
            password = kwargs['kwargs']['user']['pass']
        else:
            username = request.POST['username']
            password = request.POST['pass']

        if 'message' in kwargs:
            page_settings['message'] = kwargs['message']

        if username is not None:
            if settings.DEBUG:
                print(username)
                print(password)
            user = authenticate(username=username, password=password)

            if user is None:
                terminal.tprint("Couldn't authenticate the user... redirect to login page", 'fail')
                page_settings['error'] = settings.SITE_NAME + " could not authenticate you. You entered an invalid username or password"
                page_settings['username'] = username
                return render(request, 'signin.html', page_settings)
            else:
                terminal.tprint('All ok', 'debug')
                login(request, user)
                if user.designation == "business_counselor":
                    return redirect('/dashboard.bc', request=request)
                elif user.designation == "business_advisor":
                    return redirect('/dashboard.ba', request=request)
                elif user.designation == "program_manager":
                    return redirect('/dashboard.pm', request=request)
                return redirect('/dashboard', request=request)
        else:
            return render(request, 'signin.html', {username: username})

    except KeyError as e:
        sentry_sdk.capture_exception(e)
        # ask the user to enter the username and/or password
        terminal.tprint('\nUsername/password not defined: %s' % str(e), 'warn')
        page_settings['message'] = page_settings['message'] if 'message' in page_settings else "Please enter your username and password"
        return render(request, 'signin.html', page_settings)
    
    except Exception as e:
        sentry_sdk.capture_exception(e)
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        page_settings['message'] = "There was an error while authenticating you. Please try again and if the error persist, please contact the system administrator"
        return render(request, 'signin.html', page_settings)


def user_logout(request):
    logout(request)
    # specifically clear this session variable
    # for key in request.session.keys(): print(key)
    if 'cur_user' in request.session:
        del request.session['cur_user']

    return redirect('/', request=request)


def update_password(uid, password, token):
    try:
        User = get_user_model()
        uuid = force_text(urlsafe_base64_decode(uid))
        user = User.objects.get(email=uuid)

        user.set_password(password)
        user.save()
        
        # send an email that the account has been activated
        email_settings = {
            'template': 'emails/general-email.html',
            'subject': '[%s] Password Updated' % settings.SITE_NAME,
            'sender_email': settings.SENDER_EMAIL,
            'recipient_email': user.email,
            'use_queue': getattr(settings, 'QUEUE_EMAILS', False),
            'title': 'Password Updated',
            'message': 'Dear %s,<br /><p>You have successfully updated your password to the %s. You can now log in using your new password.</p>' % (user.first_name, settings.SITE_NAME),
        }
        notify = Notification()
        notify.send_email(email_settings)

        return user.email

    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        raise


def activate_user(request, user, token):
    try:
        uid = force_text(urlsafe_base64_decode(user))
        user = User.objects.get(pk=uid)

        activation_view = ActivationView()
        activation_view.validate_key(token)

        user.is_active = True
        user.save()

        # send an email that the account has been activated
        email_settings = {
            'template': 'emails/general-email.html',
            'subject': '[%s] Account Activated' % settings.SITE_NAME,
            'sender_email': settings.SENDER_EMAIL,
            'recipient_email': user.email,
            'use_queue': getattr(settings, 'QUEUE_EMAILS', False),
            'title': 'Account Activated',
            'message': 'Thank you for confirming your email. Your account at %s is now active.' % settings.SITE_NAME,
        }
        notify = Notification()
        notify.send_email(email_settings)
        
        uid = urlsafe_base64_encode(force_bytes(user.email))
        token = default_token_generator.make_token(user)
        return HttpResponseRedirect(reverse('new_user_password', kwargs={'uid':uid}))
    
    except ActivationError as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return reverse('home', kwargs={'error': True, 'message': e.message})

    except User.DoesNotExist as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return reverse('home', kwargs={'error': True, 'message': 'The specified user doesnt exist' })

    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return reverse('home', kwargs={'error': True, 'message': 'There was an error while activating your account. Contact the system administrator' })


def new_user_password(request, uid=None, token=None, *args, **kwargs):
    # the uid can be generated from a redirect when a user confirms their account
    # if not set, the user will have set their email on a user page
    current_site = get_current_site(request)
    params = {'site_name': settings.SITE_NAME, 'page_title': settings.SITE_NAME}
    
    # the uid is actually an encoded email
    try:
        if uid:
            if token is None:
                uuid = force_text(urlsafe_base64_decode(uid))
                user = User.objects.get(email=uuid)
                token = default_token_generator.make_token(user)
            
            # we have a user id and token, so we can present the new password page
            params['recover_token'] = token
            params['recover_user'] = uid
            return render(request, 'signin.html', params)
        else:
            # lets send an email with the reset link
            print(request.POST.get('email'))
            user = User.objects.filter(email=request.POST.get('email')).get()
            notify = Notification()
            uid = urlsafe_base64_encode(force_bytes(user.email))
            token = default_token_generator.make_token(user)
            email_settings = {
                'template': 'emails/verify_account.html',
                'subject': '[%s] Password Recovery Link' % settings.SITE_NAME,
                'sender_email': settings.SENDER_EMAIL,
                'recipient_email': user.email,
                'title': 'Password Recovery Link',
                'salutation': 'Dear %s' % user.first_name,
                'use_queue': getattr(settings, 'QUEUE_EMAILS', False),
                'verification_link': 'http://%s/new_user_password/%s/%s' % (current_site.domain, uid, token),
                'message': 'Someone, hopefully you tried to reset their password on %s. Please click on the link below to reset your password.' % settings.SITE_NAME,
                'message_sub_heading': 'Password Reset'
            }
            notify.send_email(email_settings)

        params['is_error'] = False
        params['message'] = 'We have sent a password recovery link to your email.'
        return render(request, 'signin.html', params)

    except User.DoesNotExist as e:
        params['error'] = True
        sentry_sdk.capture_exception(e)
        params['message'] = 'Sorry, but the specified user is not found in our system'
        return render(request, 'signin.html', params)

    except Exception as e:
        if settings.DEBUG: print(str(e))
        sentry_sdk.capture_exception(e)
        return render(request, 'signin.html', {'site_name': settings.SITE_NAME, 'is_error': True, 'message': 'There was an error while saving the new password'})


def recover_password(request):
    current_site = get_current_site(request)
    # the uid is actually an encoded email
    params = {'site_name': settings.SITE_NAME, 'token': ''}
    return render(request, 'signin.html', params)


def save_user_password(request):
    # save the user password and redirect to the dashboard page
    try:
        passwd = request.POST.get('pass')
        repeat_passwd = request.POST.get('repeat_pass')
        uid = request.POST.get('uuid')
        token = request.POST.get('uu_token')

        if passwd != repeat_passwd:
            params = {'site_name': settings.SITE_NAME, 'recover_token': token, 'recover_user': uid, 'is_error': True, 'message': 'The entered passwords dont match. Please try again.'}
            return render(request, 'signin.html', params)

        u_email = update_password(uid, passwd, token)
        u_user = User.objects.get(email=u_email)

        # seems all is good, now login and return the dashboard
        message='You have set a new password successfully. Please log in using the new password.'
        return login_page(request, kwargs={ 'user': {'pass': passwd, 'username': u_user.username} })
    except Exception as e:
        if settings.DEBUG: print(str(e))
        sentry_sdk.capture_exception(e)
        return render(request, 'signin.html', {'site_name': settings.SITE_NAME, 'is_error': True, 'message': 'There was an error while saving the new password'})


@login_required(login_url='/login')
def get_ajax_data(request, d_type, filter_ = None):
    
    try:
        validate_user_access(request, d_type)

        to_return = {}
        if filter_:
            f = re.search('^(.+)_(\d+)', filter_)
            if f:
                feature_name = f[1]
                feature_code = int(f[2])
                filters = {} if feature_code == 0 else { 'code': feature_code }
        else:
            feature_code = 0
            filters = {}

        if d_type == 'users':
            all_users = Personnel.objects.order_by('first_name').all()
            data_to_return = PersonnelSerializer(all_users, many=True, context={'request': request})
            to_return['data'] = data_to_return.data

        elif d_type == 'exported_files':
            analyser = Analyser()
            analyser.process_uploaded_files()

            to_return = analyser.get_all_chats(request)

        elif d_type == 'search':
            all_suggestions = []
            search_query = request.POST.get('query')

            all_groups = WhatsAppGroup.objects.filter(group_name__icontains=search_query).all()
            all_groups_ser = WhatsAppGroupSerializer(all_groups, many=True, context={'request': request})
            for grp in all_groups_ser.data: all_suggestions.append({'value': grp['group_name'], 'data': {'category': 'Group', 'id': grp['pk_id']} })

            all_users = UserDailyStats.objects.select_related('group').filter(name_phone__icontains=search_query).values('name_phone', 'group__group_name', 'group_id').annotate(a=Count('name_phone', distinct=True), b=Count('group_id', distinct=True)).all()
            for user in all_users:
                all_suggestions.append({'value': '%s - %s' % (user['name_phone'], user['group__group_name']), 'data': {'category': 'User', 'user': user['name_phone'], 'group_id': my_hashids.encode(user['group_id'])} })

            to_return = {
                'query': search_query,
                'suggestions': all_suggestions
            }

        elif d_type == 'engaged_users':
            analyser = Analyser()
            to_return = analyser.fetch_engaged_users(request)

        return JsonResponse(to_return, status=200, safe=False)

    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return JsonResponse({'error': "There was an error while fetching data from the server. Please contact the system administrator."}, status=500, safe=False)


@login_required(login_url='/login')
def dashboard(request, *args, **kwargs):
    try:
        params = get_basic_info(request)

        if 'error' in kwargs:
            params['error'] = kwargs['error']
            params['message'] = kwargs['message']
        params['page_title'] = 'Dashboard'
        params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']

        try:
            date_range = request.POST.get('range')
        except:
            date_range = None

        analyser = Analyser()
        params['stats'] = analyser.fetch_all_meta(date_range)
        params['has_data'] = False if params['stats']['empty_db'] else True

        return render(request, 'dashboard/dashboard.html', params)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        # we need a default page to go to
        return index(request, error=True, message='There was an error while getting a list of the WhatsApp groups. Please contact the system administrator')

@login_required(login_url='/login')
def dashboardPM(request, *args, **kwargs):
    try:
        params = get_basic_info(request)

        if 'error' in kwargs:
            params['error'] = kwargs['error']
            params['message'] = kwargs['message']
        params['page_title'] = 'Dashboard'
        params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']

        try:
            date_range = request.POST.get('range')
        except:
            date_range = None

        analyser = Analyser()
        params['stats'] = analyser.fetch_all_meta(date_range)
        params['has_data'] = False if params['stats']['empty_db'] else True

        return render(request, 'dashboard/dashboard.pm.html', params)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        # we need a default page to go to
        return index(request, error=True, message='There was an error while getting a list of the WhatsApp groups. Please contact the system administrator')

@login_required(login_url='/login')
def dashboardBA(request, *args, **kwargs):
    try:
        params = get_basic_info(request)

        if 'error' in kwargs:
            params['error'] = kwargs['error']
            params['message'] = kwargs['message']
        params['page_title'] = 'Dashboard'
        params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']

        try:
            date_range = request.POST.get('range')
        except:
            date_range = None

        analyser = Analyser()
        params['stats'] = analyser.fetch_all_meta(date_range)
        params['has_data'] = False if params['stats']['empty_db'] else True

        return render(request, 'dashboard/dashboard.ba.html', params)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        # we need a default page to go to
        return index(request, error=True, message='There was an error while getting a list of the WhatsApp groups. Please contact the system administrator')

@login_required(login_url='/login')
def dashboardBC(request, *args, **kwargs):
    try:
        params = get_basic_info(request)

        if 'error' in kwargs:
            params['error'] = kwargs['error']
            params['message'] = kwargs['message']
        params['page_title'] = 'Dashboard'
        params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']

        try:
            date_range = request.POST.get('range')
        except:
            date_range = None

        analyser = Analyser()
        params['stats'] = analyser.fetch_all_meta(date_range)
        params['has_data'] = False if params['stats']['empty_db'] else True

        return render(request, 'dashboard/dashboard.bc.html', params)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        # we need a default page to go to
        return index(request, error=True, message='There was an error while getting a list of the WhatsApp groups. Please contact the system administrator')


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


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'data_manager' or u.designation == 'system_admin', login_url='/dashboard')
def list_whatsapp_chats(request):
    
    try:
        params = get_basic_info(request)

        analyser = Analyser()
        params['data'] = analyser.fetch_groups_info()

        params['page_title'] = 'WhatsApp Groups'
        params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']

        return render(request, 'dashboard/whatsapp_groups.html', params)
    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return dashboard(request, error=True, message='There was an error while getting a list of the WhatsApp groups. Please contact the system administrator')


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'data_manager' or u.designation == 'system_admin', login_url='/dashboard')
def list_whatsapp_users(request):
    
    try:
        params = get_basic_info(request)

        params['page_title'] = 'Engaged Users'
        params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']

        return render(request, 'dashboard/whatsapp_users.html', params)
    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return dashboard(request, error=True, message='There was an error while getting a list of enagaged users. Please contact the system administrator')


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'data_manager' or u.designation == 'system_admin', login_url='/dashboard')
def list_exported_files(request):
    
    try:
        params = get_basic_info(request)
        params['page_title'] = 'Exported Chats'
        params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']

        return render(request, 'dashboard/exported_chats.html', params)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return dashboard(request, error=True, message='There was an error while getting a list of the exported files. Please contact the system administrator')


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'data_manager' or u.designation == 'system_admin' or u.designation == 'business_counselor' or u.designation == 'business_advisor' or u.designation == 'program_manager', login_url='/dashboard')
def show_group_stats(request, uid):
    
    try:
        params = get_basic_info(request)
        params['page_title'] = 'Group Statistics'
        params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']

        group_id=int(my_hashids.decode(uid)[0])
        try:
            date_range = request.POST.get('range')
        except:
            date_range = None

        analyser = Analyser()
        params['stats'] = analyser.fetch_group_meta(group_id, date_range)
        params['name_changes'] = params['stats']['name_changes']
        params['stats'].pop('name_changes')

        return render(request, 'dashboard/group_stats.html', params)
    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return dashboard(request, error=True, message='There was an error while generating the analysis for the selected group. Please contact the system administrator')


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'data_manager' or u.designation == 'system_admin' or u.designation == 'business_counselor' or u.designation == 'business_advisor' or u.designation == 'program_manager', login_url='/dashboard')
def show_user_stats(request, gid, user_):
    
    try:
        params = get_basic_info(request)
        group_id=int(my_hashids.decode(gid)[0])
        params['page_title'] = 'User Statistics'
        params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']

        try:
            date_range = request.POST.get('range')
        except:
            date_range = None

        analyser = Analyser()
        params['stats'] = analyser.fetch_user_meta(group_id, user_, date_range)

        return render(request, 'dashboard/user_stats.html', params)
    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        mssg = 'There was an error while generating the analysis for the selected user - %s' % user_
        return dashboard(request, error=True, message='%s. Please contact the system administrator' % mssg)

@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'data_manager' or u.designation == 'system_admin' or u.designation == 'business_counselor' or u.designation == 'business_advisor' or u.designation == 'program_manager', login_url='/dashboard')
def global_search(request):
    
    try:
        pass
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return None


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'system_admin', login_url='/dashboard')
def users(request):
    
    params = get_basic_info(request)
    params['page_title'] = 'System Users'
    params['site_name'] = settings.SITE_NAME + ' - ' + params['page_title']
    params['sysusers_active'] = 'active'
    params['user_types'] = PERSONNEL_DESIGNATION_CHOICES

    return render(request, 'dashboard/users.html', params)


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'system_admin', login_url='/dashboard')
def validate_objects(request):
    
    for key, value in request.GET.items():
        if key == 'tel':
            # check that this telephone is not already used
            to_return = "true" if Personnel.objects.filter(tel=value).first() is None else "false"
        elif key == 'email':
            # check that this telephone is not already used
            to_return = "true" if Personnel.objects.filter(email=value).first() is None else "false"
        elif key == 'username':
            # check that this telephone is not already used
            to_return = "true" if Personnel.objects.filter(username=value).first() is None else "false"

    return HttpResponse(to_return)


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'system_admin', login_url='/dashboard')
def add_objects(request, d_type):
    
    params = get_basic_info(request)

    try:
        if d_type == 'add_user':
            # adding a user
            # this should be an admin or super admin
            if request.session['cu_issuperuser'] or request.session['designation'] == 'system_admin':
                ret = add_user(request)
                return JsonResponse(ret)
            else:
                return JsonResponse({'error': False, 'message': "Sorry, you don't have the necessary permissions to perform this action."})

    except DataError as e:
        transaction.rollback();
        if settings.DEBUG: terminal.tprint('%s (%s)' % (str(e), type(e)), 'fail')
        sentry_sdk.capture_exception(e)
        return JsonResponse({'error': True, 'message': 'Please check the number of items being issued/received'})

    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return JsonResponse({'error': True, 'message': 'There was an error while updating the database'})


def add_user(request):
    # given a user details add the user
    # 1. Get the next personnel code
    # 1. Add the details of the user and set is_active to 0. Generate a password
    # 2. Send email to the user with the activation link
    
    try:
        nickname=request.POST.get('username')
        username=request.POST.get('username')
        designation=request.POST.get('designation')
        tel=request.POST.get('tel')
        email=request.POST.get('email')
        first_name=request.POST.get('first_name')
        last_name=request.POST.get('surname')

        new_user = User(
            nickname=username,
            username=username,
            designation=designation,
            tel=tel,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=make_password('SomeCrazyPasswordForStaters'),
            is_active=0
        )
        new_user.full_clean()
        new_user.save()

        reg_view = RegistrationView()
        activation_link = reg_view.get_activation_key(new_user)

        # send an email to this user
        notify = Notification()
        uid = urlsafe_base64_encode(force_bytes(new_user.pk))
        current_site = get_current_site(request)

        email_settings = {
            'template': 'emails/verify_account.html',
            'subject': '[%s] Confirm Registration' % settings.SITE_NAME,
            'sender_email': settings.SENDER_EMAIL,
            'recipient_email': email,
            'site_name': settings.SITE_NAME,
            'site_url': 'http://%s' % current_site.domain,
            'title': 'Confirm Registration',
            'salutation': 'Dear %s' % first_name,
            'use_queue': getattr(settings, 'QUEUE_EMAILS', False),
            'verification_link': 'http://%s/activate_new_user/%s/%s' % (current_site.domain, uid, activation_link),
            'message': 'You have been registered successfully to the %s. We are glad to have you on board. Please click on the button below to activate your account. You will not be able to use your account until it is activated. The activation link will expire in %d hours' % (settings.SITE_NAME, settings.ACCOUNT_ACTIVATION_DAYS * 24),
            'message_sub_heading': 'You have been registered successfully'
        }
        notify.send_email(email_settings)

        return {'error': False, 'message': 'The user has been saved successfully'}
    
    except ValidationError as e:
        return {'error': True, 'message': 'There was an error while saving the user: %s' % str(e)}
    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        raise


@login_required(login_url='/login')
def edit_objects(request, d_type):
    
    params = get_basic_info(request)

    try:
        pk_id = my_hashids.decode(request.POST.get('object_id'))[0]
        

    except DataError as e:
        transaction.rollback();
        if settings.DEBUG: terminal.tprint('%s (%s)' % (str(e), type(e)), 'fail')
        sentry_sdk.capture_exception(e)
        return JsonResponse({'error': True, 'message': 'Please check the entered data'})

    except Exception as e:
        if settings.DEBUG: terminal.tprint('%s (%s)' % (str(e), type(e)), 'fail')
        sentry_sdk.capture_exception(e)
        return JsonResponse({'error': True, 'message': 'There was an error while updating the database'})


@login_required(login_url='/login')
def delete_objects(request, d_type):
    params = get_basic_info(request)

    try:
        pk_id = my_hashids.decode(request.POST.get('object_id'))[0]

        if d_type == 'delete_user':
            user = User.objects.filter(id=pk_id).get()
            user.delete()

            return JsonResponse({'error': False, 'message': 'The user has been deleted successfully'})


    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return JsonResponse({'error': True, 'message': 'There was an error while updating the database'})

@login_required(login_url='/login')
def resend_activation_email(request):
    params = get_basic_info(request)

    try:
        pk_id = my_hashids.decode(request.POST.get('object_id'))[0]
        user = User.objects.filter(id=pk_id).get()

        reg_view = RegistrationView()
        activation_link = reg_view.get_activation_key(user)

        # send an email to this user
        notify = Notification()
        uid = user.id #urlsafe_base64_encode(force_bytes(user.id))
        current_site = get_current_site(request)


        terminal.tprint('###########################in resend', 'debug')
        #terminal.tprint(uid, 'debug')

        email_settings = {
            'template': 'emails/verify_account.html',
            'subject': '[%s] Confirm Registration' % settings.SITE_NAME,
            'sender_email': settings.SENDER_EMAIL,
            'recipient_email': user.email,
            'site_name': settings.SITE_NAME,
            'site_url': 'http://%s' % current_site.domain,
            'title': 'Confirm Registration',
            'salutation': 'Dear %s' % user.first_name,
            'use_queue': getattr(settings, 'QUEUE_EMAILS', False),
            'verification_link': 'http://%s/activate_new_user/%s/%s' % (current_site.domain, uid, activation_link),
            'message': 'You have been registered successfully to the %s. We are glad to have you on board. Please click on the button below to activate your account. You will not be able to use your account until it is activated. The activation link will expire in %d hours' % (settings.SITE_NAME, settings.ACCOUNT_ACTIVATION_DAYS * 24),
            'message_sub_heading': 'You have been registered successfully'
        }
        notify.send_email(email_settings)

        return JsonResponse({'error': False, 'message': 'Activation email successfully sent'})

    

    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return JsonResponse({'error': True, 'message': 'There was an error while updating the database'})


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'system_admin', login_url='/dashboard')
def manage_objects(request):
    
    params = get_basic_info(request)
    u = User.objects.get(id=request.user.id)
    current_path = request.path.strip("/")

    try:
        # object_id = request.POST['object_id']
        object_id = my_hashids.decode(request.POST.get('object_id'))[0]

        if re.search('recipient|user$', current_path):
            cur_object = User.objects.filter(id=object_id).get()


        if re.search('^delete', current_path) and u.designation == 'system_admin':
            cur_object.delete()
            return HttpResponse(json.dumps({'error': False, 'message': 'The %s has been deleted successfully' % re.search('_(.+)$', current_path).group(1)}))
        
        elif re.search('^deactivate', current_path) and (u.designation == 'system_admin' or u.is_superuser):
            cur_object.is_active = not cur_object.is_active
            cur_object.save()
            to_return = json.dumps({'error': False, 'message': 'The %s has been updated successfully' % re.search('_(.+)$', current_path).group(1)})
        
        elif re.search('^activate', current_path) and (u.designation == 'system_admin' or u.is_superuser):
            cur_object.is_active = not cur_object.is_active
            cur_object.save()
            to_return = json.dumps({'error': False, 'message': 'The %s has been updated successfully' % re.search('_(.+)$', current_path).group(1)})

        else:
            info_message = "Couldn't perform the requested action. Confirm if you have the proper permissions to conduct this action."
            # sentry.captureMessage(info_message, level='info', extra={'user_designation': u.designation, 'request': current_path})
            u.designation == 'system_admin'
            # sentry_sdk.capture_exception(info_message)
            return JsonResponse({'error': True, 'message': info_message}, safe=False)


        return HttpResponse(to_return)

    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return HttpResponse(json.dumps({'error': True, 'message': 'There was an error while managing the %s' % re.search('_(.+)$', current_path).group(1)}))


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser or u.designation == 'system_admin', login_url='/dashboard')
def process_new_chats(request):
    try:
        params = get_basic_info(request)
        analyser = Analyser()
        analyser.process_pending_chats()
        info_message = 'The processing has completed successfully'

        return JsonResponse({'error': False, 'message': info_message}, safe=False)
    except Exception as e:
        if settings.DEBUG: terminal.tprint(str(e), 'fail')
        sentry_sdk.capture_exception(e)
        return HttpResponse(json.dumps({'error': True, 'message': 'There was an error while processing the new files. Check your email.'}))
