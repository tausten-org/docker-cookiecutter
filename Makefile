ifeq ($(strip $(DEV_CONTAINER)),)
	DOCKER_COMPOSE_PROJECT_NAME := docker-cookiecutter_devcontainer
	DOCKER_COMPOSE := docker-compose -p $(DOCKER_COMPOSE_PROJECT_NAME) -f .devcontainer/docker-compose.yml
	DOCKER_COMPOSE_EXEC := $(DOCKER_COMPOSE) exec -T app
else
	DOCKER_COMPOSE := \#
	DOCKER_COMPOSE_EXEC := $()
endif

.PHONY: up down test

run.detached:
	$(DOCKER_COMPOSE) up -d --no-recreate

test: run.detached
	$(DOCKER_COMPOSE_EXEC) echo TODO: Testing...
