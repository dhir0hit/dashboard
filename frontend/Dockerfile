# Frontend: Vite build in node, then nginx serve the built static dist.
# nginx proxies /api and /wallpapers to the backend service so the SPA
# stays same-origin and no CORS configuration is needed in production.

# ---- build stage ----
FROM node:20-slim AS build
WORKDIR /app

# Install deps first for layer caching.
COPY package.json package-lock.json* /app/
RUN npm ci || npm install

# Copy the rest of the source and build.
COPY . /app/
# VITE_API_BASE is empty by default — nginx proxies same-origin, so the
# frontend just uses relative paths (/api/..., /wallpapers/...).
ENV VITE_API_BASE=""
RUN npm run build


# ---- serve stage ----
FROM nginx:1.27-alpine AS runtime

# nginx config that serves the SPA and reverse-proxies API routes.
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]