FROM python:3.14-slim
# TODO: Install ssh-keygen

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    openssh-client \
    rsync \
    --no-install-recommends

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

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uv", "run", "kopf", "run", "-m", "devservers.operator"]
