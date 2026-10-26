// The demo sign-in gate (design §16.1, D-22): one username and password from the deployment's
// environment, a signed session cookie for pages, and the same credential sent to the API as
// HTTP basic auth. Web Crypto only, so it runs in middleware and route handlers alike.

export const SESSION_COOKIE = "cairn_session";
export const SESSION_TTL_SECONDS = 12 * 60 * 60;

export type GateConfig = { user: string; password: string; secret: string };

/** off: no sign-in (local dev, the VM's own web container); broken: refuse everything. */
export type Gate =
  | { kind: "off" }
  | { kind: "on"; config: GateConfig }
  | { kind: "broken"; missing: string[] };

const NAMES = ["DEMO_USER", "DEMO_PASSWORD", "SESSION_SECRET"] as const;

/** On Vercel the gate is mandatory: a missing variable fails closed instead of opening the app. */
export function gateFrom(env: Record<string, string | undefined>): Gate {
  const missing = NAMES.filter((name) => !env[name]);
  if (missing.length === NAMES.length && !env.VERCEL) return { kind: "off" };
  if (missing.length > 0) return { kind: "broken", missing };
  return {
    kind: "on",
    config: { user: env.DEMO_USER!, password: env.DEMO_PASSWORD!, secret: env.SESSION_SECRET! },
  };
}

const encoder = new TextEncoder();

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, [
    "sign",
    "verify",
  ]);
}

// The user is signed, not carried: changing DEMO_USER (or SESSION_SECRET) ends every session.
const signed = (expires: number, user: string) => encoder.encode(`${expires}\u0000${user}`);

/** `<expiry seconds>.<hex HMAC of expiry and user>`. */
export async function signSession(user: string, secret: string, nowMs: number): Promise<string> {
  const expires = Math.floor(nowMs / 1000) + SESSION_TTL_SECONDS;
  const signature = new Uint8Array(await crypto.subtle.sign("HMAC", await hmacKey(secret), signed(expires, user)));
  return `${expires}.${Array.from(signature, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

/** True for an unexpired session signed with this secret for this user. */
export async function verifySession(token: string, config: GateConfig, nowMs: number): Promise<boolean> {
  const match = /^(\d+)\.([0-9a-f]{64})$/.exec(token);
  if (!match) return false;
  const expires = Number(match[1]);
  if (expires * 1000 <= nowMs) return false;
  const signature = Uint8Array.from(match[2].match(/../g)!, (pair) => parseInt(pair, 16));
  return crypto.subtle.verify("HMAC", await hmacKey(config.secret), signature, signed(expires, config.user));
}

/** Constant-time comparison of the submitted credential (via HMAC digests of equal length). */
export async function credentialsMatch(user: string, password: string, config: GateConfig): Promise<boolean> {
  const key = await hmacKey(config.secret);
  const digest = async (text: string) =>
    new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(text)));
  const [given, expected] = await Promise.all([
    digest(`${user}\u0000${password}`),
    digest(`${config.user}\u0000${config.password}`),
  ]);
  let difference = 0;
  for (let i = 0; i < expected.length; i++) difference |= given[i] ^ expected[i];
  return difference === 0;
}

const HERE = "https://cairn.invalid";

/**
 * Where to go after signing in: a path on this site only. Resolved as a browser would (which drops
 * tabs and newlines and reads `\\` as `/`), and only the normalised path, query and hash returned.
 */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || /[\u0000-\u001f\\\\]/.test(next)) return "/cases";
  try {
    const url = new URL(next, HERE);
    return url.origin === HERE ? url.pathname + url.search + url.hash : "/cases";
  } catch {
    return "/cases";
  }
}
