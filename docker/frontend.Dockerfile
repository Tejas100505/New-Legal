# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Copy custom nginx config
COPY --from=builder /build/dist /usr/share/nginx/html

# Nginx config is mounted via Docker Compose (docker/nginx.conf)
# but provide a default COPY for standalone builds
COPY ../docker/nginx.conf /etc/nginx/conf.d/default.conf 2>/dev/null || true

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
