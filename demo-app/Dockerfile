# pull official base image
FROM python:3.11-slim AS base


ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  # Poetry's configuration:
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR='/var/cache/pypoetry' \
  POETRY_HOME='/usr/local' \
  POETRY_VERSION=1.8.3

RUN apt-get update && apt-get upgrade -y \
  && apt-get install --no-install-recommends -y \
    curl \
  # Poetry
  && curl -sSL 'https://install.python-poetry.org' | python3 - \
  && poetry --version \
  # Cleaning cache:
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# set working directory
RUN mkdir /demo-app
WORKDIR /demo-app

COPY ./poetry.lock ./pyproject.toml README.md /demo-app/

FROM base AS service
# Project initialization:
RUN poetry install --without dev --no-interaction --no-ansi
COPY ./demo_app /demo-app/demo_app
ENTRYPOINT ["uvicorn", "demo_app.main:app", "--reload", "--workers", "1", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS test
# Project initialization:
RUN poetry install --no-interaction --no-ansi
COPY ./demo_app /demo-app/demo_app
COPY ./tests /demo-app/tests
