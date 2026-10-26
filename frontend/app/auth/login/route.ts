import { type NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE, SESSION_TTL_SECONDS, credentialsMatch, gateFrom, signSession } from "@/lib/auth/session";

// The API's error shape (design §11), so the page reads it with the same helpers.
const failure = (status: number, code: string, message: string) =>
  NextResponse.json({ error: { code, message } }, { status });

/** Checks the demo credential and sets the session cookie (design §16.1). */
export async function POST(request: NextRequest) {
  const gate = gateFrom(process.env);
  if (gate.kind !== "on") {
    return failure(gate.kind === "off" ? 404 : 503, "sign_in_off", "Sign-in is not enabled here.");
  }
  const body: unknown = await request.json().catch(() => null);
  const user = typeof body === "object" && body && "user" in body ? String(body.user) : "";
  const password = typeof body === "object" && body && "password" in body ? String(body.password) : "";
  if (!(await credentialsMatch(user, password, gate.config))) {
    return failure(401, "wrong_credentials", "Wrong username or password.");
  }
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, await signSession(gate.config.user, gate.config.secret, Date.now()), {
    httpOnly: true,
    secure: request.nextUrl.protocol === "https:",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
  return response;
}
