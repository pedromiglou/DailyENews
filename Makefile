GUNICORN_CONF = example_conf/gunicorn.py
LOG_CONFIG = example_conf/logging.ini
CONF_FILE ?= example_conf/jarr.json
SERVER_PORT = 8000
SERVER_ADDR = 0.0.0.0
DB_VER = $(shell pipenv run flask db heads | tail -n1 | sed -e 's/ .*//g')
COMPOSE_FILE ?= Dockerfiles/dev-env.yml
RUN = FLASK_APP=wsgi PIPENV_IGNORE_VIRTUALENVS=1 pipenv run
COMPOSE = $(RUN) docker-compose --project-name jarr --file $(COMPOSE_FILE)
TEST = tests/
DB_NAME ?= jarr
PUBLIC_URL ?= /app
REACT_APP_API_URL ?= /api
QUEUE ?= jarr,jarr-crawling,jarr-clustering
DB_CONTAINER_NAME = postgres
QU_CONTAINER_NAME = rabbitmq

build-base:
	docker build . --file Dockerfiles/pythonbase -t pythonbase

build-server:
	docker build . --file Dockerfiles/server -t registry.deti:5000/gic2/server

push-server:
	docker push registry.deti:5000/gic2/server

build-worker:
	docker build . --file Dockerfiles/worker -t registry.deti:5000/gic2/worker

push-worker:
	docker push registry.deti:5000/gic2/worker

build-client:
	docker build . --file Dockerfiles/client -t registry.deti:5000/gic2/client \
		--build-arg PUBLIC_URL=$(PUBLIC_URL) \
		--build-arg REACT_APP_API_URL=$(REACT_APP_API_URL)

push-client:
	docker push registry.deti:5000/gic2/client

build-promo:
	docker build . --file Dockerfiles/promo -t registry.deti:5000/gic2/promo

push-promo:
	docker push registry.deti:5000/gic2/promo

tag-postgres:
	docker tag postgres:13 registry.deti:5000/gic2/postgres

push-postgres:
	docker push registry.deti:5000/gic2/postgres

tag-redis:
	docker tag redis registry.deti:5000/gic2/redis

push-redis:
	docker push registry.deti:5000/gic2/redis

tag-rabbitmq:
	docker tag rabbitmq registry.deti:5000/gic2/rabbitmq

push-rabbitmq:
	docker push registry.deti:5000/gic2/rabbitmq

########## original commands below ##########

install:
	pipenv sync --dev

pep8:
	$(RUN) pycodestyle --ignore=E126,E127,E128,W503 jarr/ --exclude=jarr/migrations

mypy:
	$(RUN) mypy jarr --ignore-missing-imports --exclude=jarr/crawler/lib/__init__.py

lint: pep8 mypy

test: export JARR_CONFIG = example_conf/jarr.test.json
test:
	$(RUN) nosetests $(TEST) -vv --with-coverage --cover-package=jarr

start-env:
	$(COMPOSE) up -d

run-server: export JARR_CONFIG = $(CONF_FILE)
run-server:
	$(RUN) gunicorn -c $(GUNICORN_CONF) -b $(SERVER_ADDR):$(SERVER_PORT) wsgi:application

run-worker: export JARR_CONFIG = $(CONF_FILE)
run-worker:
	$(RUN) celery --app ep_celery.celery_app worker -Q $(QUEUE) --hostname "$(QUEUE)@%h"

run-client:
	cd jsclient/; yarn start

db-bootstrap-user:
	$(COMPOSE) exec $(DB_CONTAINER_NAME) su postgres -c \
		"createuser $(DB_NAME) --no-superuser --createdb --no-createrole"

db-bootstrap-tables:
	$(COMPOSE) exec $(DB_CONTAINER_NAME) su postgres -c "createdb $(DB_NAME) --no-password"

db-import-dump:
	docker cp $(DUMP) jarr_$(DB_CONTAINER_NAME)_1:/tmp/dump.pgsql
	$(COMPOSE) exec $(DB_CONTAINER_NAME) su postgres -c "pg_restore -d $(DB_NAME) /tmp/dump.pgsql"
	$(COMPOSE) exec $(DB_CONTAINER_NAME) rm /tmp/dump.pgsql

init-env: export JARR_CONFIG = $(CONF_FILE)
init-env:
	$(RUN) flask bootstrap-database
	$(RUN) flask db stamp $(DB_VER)

stop-env:
	$(COMPOSE) down --remove-orphans

clean-env: stop-env
	$(COMPOSE) rm --force

status-env:
	$(COMPOSE) ps

setup-testing: export DB_NAME=jarr_test
setup-testing: export JARR_CONFIG=example_conf/jarr.test.json
setup-testing: export CONF_FILE=example_conf/jarr.test.json
setup-testing:
	make start-env
	@echo "### waiting for database to be available"
	sleep 2
	make db-bootstrap-user
	make db-bootstrap-tables
	make init-env

init-rabbitmq:
	$(COMPOSE) exec $(QU_CONTAINER_NAME) rabbitmqctl add_user jarr jarr
	$(COMPOSE) exec $(QU_CONTAINER_NAME) rabbitmqctl add_vhost jarr
	$(COMPOSE) exec $(QU_CONTAINER_NAME) rabbitmqctl set_user_tags jarr
	$(COMPOSE) exec $(QU_CONTAINER_NAME) rabbitmqctl set_permissions -p jarr jarr ".*" ".*" ".*"

init-worker:
	$(RUN) python -c "from jarr.crawler.main import scheduler;scheduler()"
