# Caddy with the rate-limit module (core Caddy has none). Versions pinned; bump together.
FROM caddy:2.10.2-builder AS build
RUN xcaddy build --with github.com/mholt/caddy-ratelimit@v0.1.0

FROM caddy:2.10.2
COPY --from=build /usr/bin/caddy /usr/bin/caddy
