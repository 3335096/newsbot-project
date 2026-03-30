import { NextRequest, NextResponse } from "next/server";
import { verifySessionToken } from "@/lib/session";
import { env } from "@/lib/env";

const PROTECTED_PREFIX = "/dashboard";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!pathname.startsWith(PROTECTED_PREFIX)) {
    return NextResponse.next();
  }

  const token = request.cookies.get(env.cookieName)?.value;
  const payload = token ? verifySessionToken(token) : null;
  if (!payload) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};
