# Next.js standalone server for the demo VM (deploy/oracle). The API is same-origin behind
# Caddy, so the browser calls relative /api/... paths (NEXT_PUBLIC_API_URL is empty).
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
ENV NEXT_PUBLIC_API_URL="" NEXT_TELEMETRY_DISABLED=1
# Next's build cache survives between deploys, so a small change rebuilds fast.
RUN --mount=type=cache,target=/app/.next/cache npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=4710 HOSTNAME=0.0.0.0
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
USER node
EXPOSE 4710
CMD ["node", "server.js"]
