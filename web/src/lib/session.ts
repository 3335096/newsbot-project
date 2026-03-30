import crypto from "node:crypto";
import { cookies } from "next/headers";

import { env } from "@/lib/env";

export type SessionUser = {
  id: number;
  role: "admin" | "editor";
  first_name?: string;
  last_name?: string;
  username?: string;
  exp: number;
};

type SessionUserInput = Omit<SessionUser, "exp">;

function base64UrlEncode(input: string): string {
  return Buffer.from(input, "utf-8").toString("base64url");
}

function base64UrlDecode(input: string): string {
  return Buffer.from(input, "base64url").toString("utf-8");
}

function sign(data: string): string {
  return crypto.createHmac("sha256", env.webAuthSecret).update(data).digest("base64url");
}

function makeExp(nowSeconds: number): number {
  return nowSeconds + Math.max(60, env.sessionTtlSeconds);
}

export function createSessionToken(payload: SessionUserInput): string {
  const body: SessionUser = {
    ...payload,
    exp: makeExp(Math.floor(Date.now() / 1000)),
  };
  const encoded = base64UrlEncode(JSON.stringify(body));
  const signature = sign(encoded);
  return `${encoded}.${signature}`;
}

export function verifySessionToken(token: string): SessionUser | null {
  const [encoded, signature] = token.split(".");
  if (!encoded || !signature) {
    return null;
  }
  const expected = sign(encoded);
  const actualBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expected);
  if (
    actualBuffer.length !== expectedBuffer.length ||
    !crypto.timingSafeEqual(actualBuffer, expectedBuffer)
  ) {
    return null;
  }

  let payload: SessionUser;
  try {
    payload = JSON.parse(base64UrlDecode(encoded)) as SessionUser;
  } catch {
    return null;
  }

  if (
    typeof payload?.id !== "number" ||
    !Number.isInteger(payload.id) ||
    (payload.role !== "admin" && payload.role !== "editor") ||
    typeof payload.exp !== "number"
  ) {
    return null;
  }
  if (payload.exp <= Math.floor(Date.now() / 1000)) {
    return null;
  }
  return payload;
}

export async function getSessionUser(): Promise<SessionUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(env.cookieName)?.value;
  if (!token) {
    return null;
  }
  return verifySessionToken(token);
}

export function getSessionFromRequest(request: Request): SessionUser | null {
  const cookieHeader = request.headers.get("cookie") || "";
  const cookieValue = cookieHeader
    .split(";")
    .map((entry) => entry.trim())
    .find((entry) => entry.startsWith(`${env.cookieName}=`))
    ?.slice(env.cookieName.length + 1);
  if (!cookieValue) {
    return null;
  }
  return verifySessionToken(cookieValue);
}

export async function clearSessionCookie(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(env.cookieName, "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
  });
}
