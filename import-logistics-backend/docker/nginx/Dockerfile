# syntax=docker/dockerfile:1
# Builds the web app and serves it, together with the reverse proxy, from one small image.
# Build context is the REPOSITORY ROOT (see docker-compose.prod.yml), so it can see both folders.

# ---- stage 1: build the single-page app --------------------------------------------------------
FROM node:20-alpine AS web
WORKDIR /frontend
# Dependencies first so they are cached until package.json changes
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
# Typechecks, then bundles: a type error fails the image build instead of shipping a broken app
RUN npm run build

# ---- stage 2: nginx ----------------------------------------------------------------------------
FROM nginx:1.27-alpine
RUN rm -f /etc/nginx/conf.d/default.conf
COPY import-logistics-backend/docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY import-logistics-backend/docker/nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=web /frontend/dist /usr/share/nginx/html
EXPOSE 80 443
