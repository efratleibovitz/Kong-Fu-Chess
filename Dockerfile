# One image for every server-side service (API Gateway, WS Gateway,
# Matchmaking, Game Server shards) - they're all part of the same Python
# package (server.*, core.*) and just start with different commands, set
# per service in docker-compose.yml. Keeps the image list short instead of
# maintaining 4 near-identical Dockerfiles.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

COPY . .

# Overridden per-service by `command:` in docker-compose.yml.
CMD ["python", "-m", "server.app"]
