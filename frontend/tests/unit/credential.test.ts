import type { MiddlewareCallbackParams } from "openapi-fetch";
import { describe, expect, it } from "vitest";

import { CREDENTIAL_KEY, basicToken, credentialMiddleware, rememberCredential } from "@/lib/auth/credential";

function memoryStore() {
  const items = new Map<string, string>();
  return {
    items,
    getItem: (key: string) => items.get(key) ?? null,
    setItem: (key: string, value: string) => void items.set(key, value),
    removeItem: (key: string) => void items.delete(key),
  };
}

function fakeLocation(pathname: string, search = "") {
  const visits: string[] = [];
  return { visits, location: { pathname, search, assign: (url: string) => void visits.push(url) } };
}

const params = (request: Request) => ({ request }) as unknown as MiddlewareCallbackParams;

describe("basicToken", () => {
  it("is base64 of user:password in UTF-8", () => {
    expect(basicToken("demo", "pw")).toBe("ZGVtbzpwdw==");
    expect(basicToken("démo", "pw")).toBe("ZMOpbW86cHc=");
  });
});

describe("credentialMiddleware", () => {
  it("sends the stored credential as basic auth, and nothing when none is stored", async () => {
    const store = memoryStore();
    const { location } = fakeLocation("/cases");
    const middleware = credentialMiddleware(() => store, () => location);

    const bare = (await middleware.onRequest!(params(new Request("https://api.test/api/cases")))) as Request;
    expect(bare.headers.get("Authorization")).toBeNull();

    rememberCredential("demo", "pw", store);
    const signed = (await middleware.onRequest!(params(new Request("https://api.test/api/cases")))) as Request;
    expect(signed.headers.get("Authorization")).toBe("Basic ZGVtbzpwdw==");
  });

  it("on a 401 forgets the credential and goes to /login with the way back", async () => {
    const store = memoryStore();
    rememberCredential("demo", "stale", store);
    const { location, visits } = fakeLocation("/cases/01CASE", "?tab=checks");
    const middleware = credentialMiddleware(() => store, () => location);

    await middleware.onResponse!({ ...params(new Request("https://api.test/x")), response: new Response(null, { status: 401 }) });

    expect(visits).toEqual(["/login?next=%2Fcases%2F01CASE%3Ftab%3Dchecks"]);
    expect(store.items.has(CREDENTIAL_KEY)).toBe(false);
  });

  it("leaves other statuses alone, and never redirects from /login itself", async () => {
    const store = memoryStore();
    rememberCredential("demo", "pw", store);
    const onCases = fakeLocation("/cases");
    const onLogin = fakeLocation("/login");

    await credentialMiddleware(() => store, () => onCases.location).onResponse!({
      ...params(new Request("https://api.test/x")),
      response: new Response(null, { status: 503 }),
    });
    await credentialMiddleware(() => store, () => onLogin.location).onResponse!({
      ...params(new Request("https://api.test/x")),
      response: new Response(null, { status: 401 }),
    });

    expect(onCases.visits).toEqual([]);
    expect(onLogin.visits).toEqual([]);
    expect(store.items.get(CREDENTIAL_KEY)).toBe("ZGVtbzpwdw==");
  });
});
