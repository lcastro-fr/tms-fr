#!/bin/bash
export DOCKER_UID=$(id -u | tr -d '\r\n')
export DOCKER_GID=$(id -g | tr -d '\r\n')
docker compose -f docker-compose.yml up --build
