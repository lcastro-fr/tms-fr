FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY .python-version pyproject.toml uv.lock /app/

RUN uv sync

COPY . /app/

CMD ["uv","run", "manage.py", "runserver", "0.0.0.0:8000"]
