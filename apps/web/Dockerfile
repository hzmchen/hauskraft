# SPDX-License-Identifier: AGPL-3.0-or-later
# web image (M0S-E11-01): build the SPA with Node 24 + pnpm, serve it with Caddy as a non-root user.
FROM node:24-slim AS build
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
WORKDIR /repo
COPY . .
RUN pnpm install --frozen-lockfile --filter "web..." \
 && pnpm --filter web build

FROM caddy:2-alpine
RUN adduser -S -D -H -u 10001 hearthos
ENV XDG_CONFIG_HOME=/tmp/caddy-config XDG_DATA_HOME=/tmp/caddy-data
COPY deploy/compose/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /repo/apps/web/dist /srv
USER hearthos
EXPOSE 8080
