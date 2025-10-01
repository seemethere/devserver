FROM ghcr.io/astral-sh/uv:debian-slim
WORKDIR /app
RUN uv venv -p 3.13 .venv
COPY requirements.txt .
RUN . .venv/bin/activate && uv pip install -r requirements.txt
COPY . .
RUN . .venv/bin/activate && uv pip install .
CMD ["python3", "-m", "devserver.operator"]