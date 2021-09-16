"""
Django settings for TNS Chat Analyser project.

Generated by 'django-admin startproject' using Django 2.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TIMEZONE = 'Africa/Nairobi'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
# MEDIA_URL = 'static/media/'
MEDIAFILES_DIRS = [
    os.path.join(BASE_DIR, 'analyser/media'),
]

NO_ITEMS_PER_PAGE = 7
ACCOUNT_ACTIVATION_DAYS = 1
SITE_NAME = 'Tafiti Chat Analysis'
SITE_ID=1

# paths and routes for uploaded media files
# MEDIA_ROOT = os.path.join(BASE_DIR, 'analyser/media')
MEDIA_ROOT = '/www/tns_whatsapp_analyser/analyser/media/'

if 'DJANGO_ADMIN_USERNAME' in os.environ:
    # SENTRY_USER = os.environ['SENTRY_USER']
    # SENTRY_PASS = os.environ['SENTRY_PASS']
    # SENTRY_PROJID = os.environ['SENTRY_PROJID']

    ADMIN_EMAIL = os.environ['ADMIN_EMAIL']
    SENDER_EMAIL = os.environ['SENDER_EMAIL']
    SMTP_SERVER = os.environ['SMTP_SERVER']
    SMTP_PORT = os.environ['SMTP_PORT']
    SENDER_PASSWORD = os.environ['SENDER_PASSWORD']
    MAIL_USERNAME = os.environ['MAIL_USERNAME']
    MAIL_FROM_NAME = os.environ['MAIL_FROM_NAME']

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ['DEFAULT_DB_NAME'],
            'USER': os.environ['DEFAULT_DB_USER'],
            'PASSWORD': os.environ['DEFAULT_DB_PASS'],
            'HOST': os.environ['DEFAULT_DB_HOST'],
            'PORT': os.environ['DEFAULT_DB_PORT'],
            'OPTIONS': {"charset": "utf8mb4"}
            # 'ATOMIC_REQUESTS': True,
        },
    }

    USE_GCP = os.environ['USE_GCP']
    USE_S3 = os.environ['USE_S3']

    AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
    AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
    AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
    AWS_S3_REGION_NAME = os.environ['AWS_S3_REGION_NAME']

    SECRET_KEY = os.environ['SECRET_KEY']
    GCP_DRIVE_ID = os.environ['GCP_DRIVE_ID']
else:
    import environ
    env = environ.Env(
        DEBUG=(bool, False)
    )
    # reading .env file
    # environ.Env.read_env(env.str('BASE_DIR', '.env'))
    environ.Env.read_env('analyser/.env')

    SENTRY_USER = env('SENTRY_USER')
    SENTRY_PASS = env('SENTRY_PASS')
    SENTRY_PROJID = env('SENTRY_PROJID')

    ADMIN_EMAIL = env('ADMIN_EMAIL')
    SENDER_EMAIL = env('SENDER_EMAIL')
    SMTP_SERVER = env('SMTP_SERVER')
    SMTP_PORT = env('SMTP_PORT')
    SENDER_PASSWORD = env('SENDER_PASSWORD')
    MAIL_USERNAME = env('MAIL_USERNAME')
    MAIL_FROM_NAME = env('MAIL_FROM_NAME')
    SECRET_KEY = env('SECRET_KEY')
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT'),
            'OPTIONS': {"charset": "utf8mb4"}
            # 'ATOMIC_REQUESTS': True,
        },
    }

    USE_S3 = env('USE_S3')
    USE_GCP = env('USE_GCP')
    GCP_DRIVE_ID = env('GCP_DRIVE_ID')

    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME')

if USE_S3 == 'True':
    print('using GCP')
    # aws settings continue
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.eu-west-2.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_LOCATION = 'static'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
else:
    STATIC_URL = '/static/'
    MEDIA_URL = "/media/"
    STATIC_ROOT = ''
    STATICFILES_DIR = ( os.path.join('static'), os.path.join(BASE_DIR, 'odk_dashboard/static'), )

# sentry DSN
# SENTRY_DSN = 'https://%s:%s@sentry.badili.co.ke/%s?verify_ssl=0' % (SENTRY_USER, SENTRY_PASS, SENTRY_PROJID)

SENTRY_DSN = 'https://9554a689d421479b96cb18b2b746e58c@o1001604.ingest.sentry.io/5961681'

# DEFAULT_LOCALE = 'EN'
DEFAULT_LOCALE = 'English (en)'
IS_DRY_RUN = False
DRY_RUN_RECORDS = 500


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# Application definition
INSTALLED_APPS = [
    # 'jet.dashboard',                        # jet.dashboard should be before jet
    # 'jet',                                  # jet should be before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.sites',
    'django.contrib.flatpages',

    'django_crontab',

    'rest_framework',
    'rest_framework.authtoken',

    'analyser',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
]

ROOT_URLCONF = 'analyser.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [os.path.join(BASE_DIR, 'templates/jinja2'), os.path.join(BASE_DIR, '../odk_dashboard/templates/jinja2') ],
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'analyser.settings.jinja2.environment',
        },
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates/django')],
        # 'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',                   # avail request variables in templates
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST  = True

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

AUTHENTICATION_BACKENDS = (
    'analyser.auth_backends.UsernameEmailTelBackend',
    # 'django.contrib.auth.backends.ModelBackend',
)
AUTH_USER_MODEL = 'analyser.Personnel'

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://127.0.0.1:8983/solr',
        'INCLUDE_SPELLING': True,
    },
}

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
       'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ]
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# The interval in minutes in which the notification script should be executed
NOTIFICATIONS_INTERVAL = 5

CRONJOBS = [
    ('8 */2 * * *', 'django.core.management.call_command', ['process_pending_chats'], {}, '>> /tmp/autoprocess_cron.log'),
]

ADMIN_EMAIL = 'badili.innovations@gmail.com'