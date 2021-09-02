ifeq ($(strip $(DEV_CONTAINER)),)
	PROJECT_NAME := docker-cookiecutter
	DOCKER_COMPOSE_PROJECT_NAME := $(PROJECT_NAME)_devcontainer
	DOCKER_COMPOSE := docker-compose -p $(DOCKER_COMPOSE_PROJECT_NAME) -f .devcontainer/docker-compose.yml
	DOCKER_COMPOSE_EXEC := $(DOCKER_COMPOSE) exec -w /$(PROJECT_NAME) -T app
else
	DOCKER_COMPOSE := \#
	DOCKER_COMPOSE_EXEC := $()
endif

.PHONY: up down test

run.detached:
	$(DOCKER_COMPOSE) up -d --no-recreate

test: run.detached test.unit test.integration

test.unit: run.detached
	$(DOCKER_COMPOSE_EXEC) pytest test/

test.integration: run.detached
	$(DOCKER_COMPOSE_EXEC) echo TODO: Integration tests go here...
