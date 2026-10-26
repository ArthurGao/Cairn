import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth/session";

/** Clears the session cookie; the page forgets the API credential itself. */
export function POST() {
  const response = new NextResponse(null, { status: 204 });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
