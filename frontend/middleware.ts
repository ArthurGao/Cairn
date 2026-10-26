import { type NextRequest, NextResponse } from "next/server";

import { loginPath } from "@/lib/auth/credential";
import { SESSION_COOKIE, gateFrom, verifySession } from "@/lib/auth/session";

// The demo sign-in gate for pages (design §16.1). Node runtime so the deployment's environment
// variables are read when a request arrives, not baked in at build time. /login and /auth/* are
// not matched at all (their route handler checks the gate itself), nor are static files.
export async function middleware(request: NextRequest) {
  const gate = gateFrom(process.env);
  if (gate.kind === "off") return NextResponse.next();
  if (gate.kind === "broken") {
    return new NextResponse(`Sign-in is not configured (${gate.missing.join(", ")} unset).`, { status: 503 });
  }
  const { pathname, search } = request.nextUrl;
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (token && (await verifySession(token, gate.config, Date.now()))) return NextResponse.next();
  return NextResponse.redirect(new URL(loginPath(pathname + search), request.url));
}

export const config = {
  runtime: "nodejs",
  matcher: ["/((?!login$|auth/|_next/static|_next/image|favicon.ico|icon.svg).*)"],
};
