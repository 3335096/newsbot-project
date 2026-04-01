import { NextRequest, NextResponse } from "next/server";

const PROTECTED_PREFIX = "/dashboard";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!pathname.startsWith(PROTECTED_PREFIX)) {
    return NextResponse.next();
  }
  const disableTelegramAuthRaw = (process.env.WEB_DISABLE_TELEGRAM_AUTH || "").trim().toLowerCase();
  const disableTelegramAuth =
    disableTelegramAuthRaw === "1" ||
    disableTelegramAuthRaw === "true" ||
    disableTelegramAuthRaw === "yes" ||
    disableTelegramAuthRaw === "on";
  if (disableTelegramAuth) {
    return NextResponse.next();
  }

  const token = request.cookies.get(process.env.WEB_SESSION_COOKIE_NAME || "newsbot_web_session")?.value;
  const payload = token ? await verifySessionToken(token) : null;
  if (!payload) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};

function decodeBase64Url(input: string): string | null {
  try {
    const normalized = input.replace(/-/g, "+").replace(/_/g, "/");
    const padding = normalized.length % 4 === 0 ? "" : "=".repeat(4 - (normalized.length % 4));
    return atob(normalized + padding);
  } catch {
    return null;
  }
}

function encodeBase64Url(input: Uint8Array): string {
  let binary = "";
  for (const charCode of input) {
    binary += String.fromCharCode(charCode);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function verifySessionToken(token: string): Promise<{ id: number; role: string; exp: number } | null> {
  const secret = process.env.WEB_AUTH_SECRET || "";
  if (!secret) {
    return null;
  }
  const [encoded, signature] = token.split(".");
  if (!encoded || !signature) {
    return null;
  }

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const digest = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(encoded));
  const expected = encodeBase64Url(new Uint8Array(digest));
  if (expected !== signature) {
    return null;
  }

  const decoded = decodeBase64Url(encoded);
  if (!decoded) {
    return null;
  }
  let payload: { id: number; role: string; exp: number };
  try {
    payload = JSON.parse(decoded) as {
      id: number;
      role: string;
      exp: number;
    };
  } catch {
    return null;
  }
  if (
    typeof payload.id !== "number" ||
    !Number.isInteger(payload.id) ||
    (payload.role !== "admin" && payload.role !== "editor") ||
    typeof payload.exp !== "number" ||
    payload.exp <= Math.floor(Date.now() / 1000)
  ) {
    return null;
  }
  return payload;
}
