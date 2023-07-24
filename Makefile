# run on open network at a certain port
# py manage.py runserver 0.0.0.0:8082
rung:
	gunicorn -w 4 config:gunicorn:dev
run:
	py manage.py runserver

# Make migrations and implement them for all installed apps
# py manage.py makemigrations
migrate:
	py manage.py migrate

# Check SQL commands to be run by a certain migration script
# sql:
# 	py manage.py sqlmigrate polls 0001

# Checks for any problems in your project without making migrations or touching the database.
check:
	py manage.py check

# Hops into the interactive Python shell and play around with the free API Django gives you. To invoke the Python shell, use this command:
shell:
	py manage.py shell

# create superuser
suser:
	py manage.py createsuperuser

# create a message file for translation
makem:
	python manage.py makemessages -l fr

# compile messages that have been created
compilem:
	python manage.py compilemessages


format:
	djhtml .

# Gathering static files in a single directory so you can serve them easily.
preparestatics:
	python manage.py collectstatic


test:
	py manage.py test
