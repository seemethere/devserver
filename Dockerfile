FROM python:3.14
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
# Install dependencies first
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Add in source code
ADD . /app

# Now do install of project
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --locked

CMD ["uv", "run", "kopf", "run", "-m", "devserver.operator"]
