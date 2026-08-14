#!/bin/bash
set -e
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
