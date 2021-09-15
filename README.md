## Tafiti Chat Analysis Documentation

Tafiti Chat Analysis, hereinafter TCA, is developed using the popular [Django framework](https://www.djangoproject.com/). It is dockerized for ease of deployment.


### The Basics

- The main settings are found in `analyser/settings/base.py`. Development specific settings are found in `analyser/settings/development.py` while production specific settings are in `analyser/settings/production.py`. Development and production settings inherit the main settings. Appropriate changes in the development or production settings suffices to run/deply TCA. However all settings in the 3 files can be changed accordingly.
- TCA is dockerized and uses docker-compose for deployment. Docker configuration
- System variables are saved in `analyser/.env` for development environment and `variables.env` for production. The `variables.env` file is required by `docker-compose.yml` when deploying using docker
- TCA is integrated with Google Drive where WhatsApp chat files are exported to. This integration uses `client_secrets.json` and `mycreds.txt`. Follow the tutorial [Google drive integration with Python](https://developers.google.com/drive/api/v3/about-sdk) for instructions on how to generate the 2 files
- The files `analyser/.env`, `variables.env`, `client_secrets.json` and `mycreds.txt` contain sensitive information and are not tracked. Sample files ending with _sample are provided for reference
- Inorder to take advantage of [gitlab's CI/CD](https://docs.gitlab.com/ee/ci/), CI/CD settings are defined in `.gitlab-ci.yml`. A fresh docker image for TCA is automatically compiled each time code is pushed to the master branch. After compiling the image, it is pushed to gitlabs repository. This image is later on downloaded when deploying TCA.
- The TCA django dependancies are listed in `requirements.txt` and can be installed via the normal way of installing python dependancies `pip install -r requirements.txt`. The dependancies are automatically installed when the docker image is being build
- TCA periodically processes the exported chats in the google drive folder. This setting can be found in the main settings file
- TCA uses [Sentry](https://sentry.io/welcome/) for error logging. Configure your settings appropriately
- TCA uses MySQL as the backend database
- To speed up the production site as well as provide a good user experience, the production site can use Amazon S3 CDN. This can be turned off so that local static files can be used. Further documentation on how to serve static files can be found [here](https://docs.djangoproject.com/en/2.2/howto/static-files/)
- TCA is configured to use nginx as the web server in production


### Docker stuff

TCA is dockerized purposefuly for deployment purposes. The docker environment can also be used in local development but this hasn't been tested.

- The steps for creating the image are contained in `Dockerfile`. `Dockerfile` is dependent on [a data analysis image](https://hub.docker.com/r/soloincc/alpine-python-wkhtmltopdf-data-analysis)
- The `docker` folder contains the basic files for deployment
- `docker/docker-entrypoint.sh` is the last to be executed when the docker containers have finished building and have been started
- `docker-compose.yml` describes the containers that will be ran as well as their properties and interdependencies. You can modify these settings to suit your production environment. However, TCA can be deployed with these default settings. `docker-compose.yml` can be used for local development while `docker-compose-prod.yml` is used for production


### Setup and configuration for production deployment

To deploy TCA via docker

- Install docker on the production server
- Install nginx and configure it appropriately. A sample config file is in `docker/nginx/docker_default.conf`
- Copy the necessary files and folders, ie. `docker`, `variables.env`, `docker-compose.yml` to the production server
- Build the docker containers using `docker-compose build` and ran them using `docker-compose up`
- Further documentation on docker and django can be found in [Quickstart: Compose and Django](https://docs.docker.com/samples/django/)
- In a production environment, it is recommended to use a CDN to serve static files. TCA can be configured to use static files served from the server hosting it. 


### Setup and configuration for development

To deploy TCA for development, it is highly encouraged to use virtual environment. A detailed documentation on what is a virtual environment and why it is encouraged can be found [here](https://realpython.com/python-virtual-environments-a-primer/)

1. Install python on your machine
2. Create your virtual environment
```python
# Python 3
$ python3 -m venv env
```
3. Activate your environment `source env/bin/activate`
4. Install the python dependancies `pip install -r requirements.txt`
5. Modify the settings, discussed above, appropriately
6. Create the database offline. The database shell is not created automatically and needs to be created offline
7. Ran the migrations to create the tables in the databases `python manage.py migrate`
8. Start the app by running `python manage.py runserver`
9. Access the app by opening `http://localhost:9033` on your browser. Remember to use the appropriate port if it was changed


Happy Coding!!