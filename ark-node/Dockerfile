# ────────── Dockerfile ──────────

# 1) Build the frontend with Node
FROM node:18 AS ui-builder
WORKDIR /scantrix-ui-web

# install dependencies & build
COPY scantrix-ui-web/package*.json ./
RUN npm ci
COPY scantrix-ui-web/ ./
RUN npm run build    # -> /scantrix-ui-web/dist

# 2) Build the backend with production-only Node
FROM node:18-slim
WORKDIR /app

# tell your app where the frontend will live
ENV FRONTEND_DIST=/app/frontend_dist
ENV PORT=8090
ENV HOST=127.0.0.1
# Allow the host to bind-mount a directory here (default: /data/outside)
ENV SPLAT_STORAGE_DIR=/data/outside
RUN mkdir -p ${SPLAT_STORAGE_DIR}
VOLUME ["${SPLAT_STORAGE_DIR}"]

# install only production deps
COPY ark-node/package*.json ./
RUN npm ci --omit=dev

# pull in the built frontend assets
COPY --from=ui-builder /scantrix-ui-web/dist ./frontend_dist

# copy your Express app
COPY ark-node/. .

EXPOSE 8090
CMD ["node", "server.js"]
