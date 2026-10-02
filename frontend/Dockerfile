FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
RUN mkdir -p /var/cache/nginx /var/run \
    && sed -i 's#pid[[:space:]]*/run/nginx.pid;#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf \
    && grep -q 'pid /tmp/nginx.pid;' /etc/nginx/nginx.conf \
    && chown -R nginx:nginx /var/cache/nginx /var/run /usr/share/nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/code-reviewer/browser /usr/share/nginx/html
USER nginx
EXPOSE 8080
