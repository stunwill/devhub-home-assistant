ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.12-alpine3.20

FROM node:24-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./package.json
RUN npm install --include=optional --no-audit --no-fund
COPY frontend ./
RUN npm run build

FROM ${BUILD_FROM}

RUN apk add --no-cache git ffmpeg

WORKDIR /app
ENV PYTHONPATH=/app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY --from=frontend-build /frontend/dist /app/frontend/dist
COPY backend /app/backend
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
