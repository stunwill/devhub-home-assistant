ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

RUN apk add --no-cache nodejs npm git

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY frontend/package.json frontend/package-lock.json /app/frontend/
RUN cd /app/frontend \
    && npm ci --include=optional \
    && npm cache clean --force
COPY frontend /app/frontend
RUN cd /app/frontend && npm run build

COPY backend /app/backend
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
