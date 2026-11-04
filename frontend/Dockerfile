FROM node:22-alpine AS build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
ARG VITE_API_URL=
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM nginx:1.27-alpine
ENV NGINX_ENVSUBST_FILTER=^API_HOST$
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --chmod=755 frontend/wait-for-api.sh /docker-entrypoint.d/40-wait-for-api.sh
COPY --from=build /app/frontend/dist /usr/share/nginx/html
EXPOSE 80