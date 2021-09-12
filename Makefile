ifeq ($(strip $(DEV_CONTAINER)),)
	PROJECT_FOLDER_NAME := $(shell basename "$(CURDIR)")
	USER_AND_GROUP := $(shell id -u):$(shell id -g)
	DOCKER_COMPOSE_PROJECT_NAME := $(PROJECT_FOLDER_NAME)_devcontainer
	DOCKER_COMPOSE := docker-compose -p $(DOCKER_COMPOSE_PROJECT_NAME) -f .devcontainer/docker-compose.yml
	DOCKER_COMPOSE_EXEC := $(DOCKER_COMPOSE) exec -w /$(PROJECT_FOLDER_NAME) -T --user $(USER_AND_GROUP) app
else
	DOCKER_COMPOSE := \#
	DOCKER_COMPOSE_EXEC := $()
endif

.PHONY: up down test

run.detached:
	$(DOCKER_COMPOSE) up -d --no-recreate

test: run.detached test.unit test.integration

test.unit: run.detached
	$(DOCKER_COMPOSE_EXEC) tox -e py39,lint,format

test.integration: run.detached
	$(DOCKER_COMPOSE_EXEC) echo TODO: Integration tests go here...
