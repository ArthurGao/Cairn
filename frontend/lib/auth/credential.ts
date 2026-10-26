// The browser half of the demo sign-in gate: after /login succeeds, the credential is kept for
// this tab only and sent to the API as HTTP basic auth (the VM's Caddy checks it, D-22). An API
// 401 means it is missing or stale: forget it and go back to /login.

import type { Middleware } from "openapi-fetch";

export const CREDENTIAL_KEY = "cairn.api-credential";
export const LOGIN_PATH = "/login";

type Store = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function browserStore(): Store | undefined {
  try {
    return typeof window === "undefined" ? undefined : window.sessionStorage;
  } catch {
    return undefined;
  }
}

/** base64 of `user:password` as UTF-8, the basic-auth token. */
export function basicToken(user: string, password: string): string {
  let binary = "";
  for (const byte of new TextEncoder().encode(`${user}:${password}`)) binary += String.fromCharCode(byte);
  return btoa(binary);
}

export function rememberCredential(user: string, password: string, store = browserStore()): void {
  store?.setItem(CREDENTIAL_KEY, basicToken(user, password));
}

export function forgetCredential(store = browserStore()): void {
  store?.removeItem(CREDENTIAL_KEY);
}

export function loginPath(currentPath: string): string {
  return `${LOGIN_PATH}?next=${encodeURIComponent(currentPath)}`;
}

/** Adds the stored credential to every API call; a 401 sends the user to /login (not from /login). */
export function credentialMiddleware(
  store: () => Store | undefined = browserStore,
  location: () => { pathname: string; search: string; assign(url: string): void } | undefined = () =>
    typeof window === "undefined" ? undefined : window.location,
): Middleware {
  return {
    onRequest({ request }) {
      const token = store()?.getItem(CREDENTIAL_KEY);
      if (token) request.headers.set("Authorization", `Basic ${token}`);
      return request;
    },
    onResponse({ response }) {
      const here = location();
      if (response.status === 401 && here && here.pathname !== LOGIN_PATH) {
        forgetCredential(store());
        here.assign(loginPath(here.pathname + here.search));
      }
      return response;
    },
  };
}
