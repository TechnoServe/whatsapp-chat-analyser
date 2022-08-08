### The Basics

- The main settings are found in `analyser/settings/base.py`. Development specific settings are found in `analyser/settings/development.py` while production specific settings are in `analyser/settings/production.py`. Development and production settings inherit the main settings. Appropriate changes in the development or production settings suffices to run/deply TCA. However all settings in the 3 files can be changed accordingly.
- System variables are saved in `analyser/.env` for development environment and `variables.env` for production.
- TCA is integrated with Google Drive where WhatsApp chat files are exported to. This integration uses `client_secrets.json` and `mycreds.txt`. Follow the tutorial [Google drive integration with Python](https://developers.google.com/drive/api/v3/about-sdk) for instructions on how to generate the 2 files
- The files `analyser/.env`, `client_secrets.json` and `mycreds.txt` contain sensitive information and are not tracked. Sample files ending with _sample are provided for reference
- The TCA django dependancies are listed in `requirements.txt` and can be installed via the normal way of installing python dependancies `pip install -r requirements.txt`. The dependancies are automatically installed when the docker image is being build
- TCA periodically processes the exported chats in the google drive folder. This setting can be found in the main settings file
- TCA uses [Sentry](https://sentry.io/welcome/) for error logging. Configure your settings appropriately
- TCA uses MySQL as the backend database
- TCA is configured to use nginx as the web server in production


## Instructions for Setting up a development Environmnent

1.  Create a Virtual Evironment

        python3 -m venv env

You only have to run step 1 once.

2.  Activate Virtual Evironment
    Kindly make sure you are in the root folder i.e whatsapp-chat-analyser and run the command below.

        source env/bin/activate

3.  Install Dependencies

        pip install -r requirements.txt

4.  Run Database Migration

        python manage.py migrate

5.  Create Django Admin User

        python manage.py createsuperuser

You will be asked to provide a username, email, and password. These credentials will be used to log into the application.

6.  Launch Application

        python manage.py runserver

7. Log into the system
   Navigate to `http://127.0.0.1:9037/` to access the system.
