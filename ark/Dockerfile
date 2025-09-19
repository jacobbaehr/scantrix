# ────────── src/ark/Dockerfile ──────────

# 1) Build the frontend with Node
FROM node:18 AS landing-page-builder
WORKDIR /scantrix-api-web

# install dependencies & build
COPY scantrix-api-web/package*.json ./
RUN npm ci
COPY scantrix-api-web/ ./
RUN npm run build    # -> /scantrix-api-web/dist

# 1) Build the frontend with Node
FROM node:18 AS demo-app-builder
WORKDIR /scantrix-ui-web

# install dependencies & build
COPY scantrix-ui-web/package*.json ./
RUN npm ci
COPY scantrix-ui-web/ ./
RUN npm run build    # -> /scantrix-ui-web/dist

# 2) Build the backend with Poetry
FROM python:3.12-slim
WORKDIR /app

# tell your app where the frontend will live
ENV LANDING_PAGE_FRONTEND_DIST=/app/landing_page_frontend_dist
ENV DEMO_APP_FRONTEND_DIST=/app/demo_app_frontend_dist

# Allow the host to bind-mount a directory here (default: /data/outside)
ENV VIDEO_PATH=/data/outside/video
RUN mkdir -p ${VIDEO_PATH}
VOLUME ["${VIDEO_PATH}"]
ENV SPLAT_STORAGE_DIR=/data/outside/splat_storage
RUN mkdir -p ${SPLAT_STORAGE_DIR}
VOLUME ["${SPLAT_STORAGE_DIR}"]

# install Poetry and your dependencies
RUN pip install --no-cache-dir poetry
COPY ark/pyproject.toml ark/poetry.lock ./
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

# pull in the built frontend assets
COPY --from=landing-page-builder /scantrix-api-web/dist ./landing_page_frontend_dist
COPY --from=demo-app-builder /scantrix-ui-web/dist ./demo_app_frontend_dist

# copy your FastAPI app
COPY ark/ .

EXPOSE 8080
CMD ["uvicorn", "src.ark.main:app", "--host", "0.0.0.0", "--port", "8080"]
