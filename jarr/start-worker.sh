#!/bin/sh

# schedule start scheduler
sleep 30 && pipenv run python3 /den/jarr/schedule.py &

# run celery worker
pipenv run celery --app ep_celery.celery_app worker