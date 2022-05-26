#!/bin/sh

# create database tables
pipenv run flask bootstrap-database

# run flask
pipenv run gunicorn -c /etc/jarr/gunicorn.py --log-config /etc/jarr/logging.ini -b 0.0.0.0:8000 wsgi:application