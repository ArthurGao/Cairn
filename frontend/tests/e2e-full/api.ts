// The API origin. In dev it is its own server; behind Caddy (deploy/oracle/rehearse.sh) it is the
// same origin as the pages.
export const API = process.env.E2E_API_URL ?? "http://localhost:4700";
