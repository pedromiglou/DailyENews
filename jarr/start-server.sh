#!/usr/bin/env bash

pipenv run flask bootstrap-database

pipenv run gunicorn -c /etc/jarr/gunicorn.py --log-config /etc/jarr/logging.ini -b 0.0.0.0:8000 wsgi:application