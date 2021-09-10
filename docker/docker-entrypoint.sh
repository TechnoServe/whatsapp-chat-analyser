#!/bin/bash
# publish our environment variables
printenv | grep -v "no_proxy" >> /etc/environment
python -c 'import sys; print(sys.path)'

# make migrations for the gallery plugin
# python manage.py makemigrations gallery
# python manage.py migrate gallery --noinput

## run migrations -- its a bad idea to run migrations automatically. Migrations should be ran manually when they are needed

# if updating the schemas
# python manage.py migrate --noinput --run-syncdb

# if creating new database connections
python manage.py migrate

## collect statics
echo "Collecting statics to AWS takes a whoooopping 25mins when bringing up the container... it should be ran when absolutely necessary...."
# echo "Collecting the static files... I will not post the progress"
# python manage.py collectstatic --noinput --verbosity 3
# python manage.py collectstatic --noinput
# echo "Finished collecting the static files"

## create superuser
# python manage.py createsuperuser

## RUN `python manage.py migrate auth` before running this:
python manage.py shell << EOF
from os import environ
from django.contrib.auth.models import User
username=environ.get('DJANGO_ADMIN_USERNAME')
password=environ.get('DJANGO_ADMIN_PASSWORD')
email=environ.get('DJANGO_ADMIN_EMAIL')
User.objects.filter(email=email).delete()
User.objects.create_superuser(username, email, password)
EOF

# install the crontab
python manage.py crontab add

# ran cron in the background
echo "Starting the cron service in the background..."
crond

## runserver
python manage.py runserver 0.0.0.0:9037
