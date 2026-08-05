FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_CACHE_DIR=/tmp/uv-cache
ENV UV_NO_SYNC=1
ENV PATH="/opt/venv/bin:$PATH"
ENV HOME=/tmp

RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY .python-version pyproject.toml uv.lock /app/

RUN uv sync && rm -rf /tmp/uv-cache

COPY . /app/

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
