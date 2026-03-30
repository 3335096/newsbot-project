import { NextRequest, NextResponse } from "next/server";

import { env } from "@/lib/env";
import { createSessionToken } from "@/lib/session";
import {
  verifyTelegramAuthPayload,
  verifyTelegramInitData,
  type TelegramAuthUser,
} from "@/lib/telegram-auth";

type LoginRequestBody = {
  mode?: "telegram_init_data" | "telegram_login_widget";
  payload?: string;
};

export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: LoginRequestBody;
  try {
    body = (await request.json()) as LoginRequestBody;
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  const rawPayload = body.payload?.trim();
  if (!rawPayload) {
    return NextResponse.json({ detail: "Missing Telegram payload" }, { status: 400 });
  }

  const mode = body.mode ?? "telegram_init_data";

  try {
    let user: TelegramAuthUser | null = null;
    if (mode === "telegram_init_data") {
      user = verifyTelegramInitData(rawPayload, env.botToken, 600)?.user ?? null;
    } else if (mode === "telegram_login_widget") {
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(rawPayload) as Record<string, unknown>;
      } catch {
        return NextResponse.json({ detail: "Invalid login widget JSON payload" }, { status: 400 });
      }
      const payloadRecord: Record<string, string> = {};
      for (const [key, value] of Object.entries(parsed)) {
        if (value === null || value === undefined) {
          continue;
        }
        if (key === "id") {
          payloadRecord[key] = String(value);
          continue;
        }
        if (key === "photo_url") {
          payloadRecord[key] = String(value);
          continue;
        }
        payloadRecord[key] = String(value);
      }
      if (payloadRecord.id) {
        payloadRecord.user = JSON.stringify({
          id: Number(payloadRecord.id),
          first_name: payloadRecord.first_name,
          last_name: payloadRecord.last_name,
          username: payloadRecord.username,
          photo_url: payloadRecord.photo_url,
        });
      }
      user = verifyTelegramAuthPayload(payloadRecord, env.botToken, 600)?.user ?? null;
    } else {
      return NextResponse.json({ detail: "Unsupported auth mode" }, { status: 400 });
    }
    if (!user) {
      return NextResponse.json({ detail: "Invalid Telegram auth payload" }, { status: 401 });
    }

    if (env.allowedUserIds.size > 0 && !env.allowedUserIds.has(user.id)) {
      return NextResponse.json({ detail: "User is not allowed" }, { status: 403 });
    }

    const token = createSessionToken({
      id: user.id,
      role: env.adminUserIds.has(user.id) ? "admin" : "editor",
      first_name: user.first_name,
      last_name: user.last_name,
      username: user.username,
    });

    const response = NextResponse.json({ ok: true });
    response.cookies.set(env.cookieName, token, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: env.sessionTtlSeconds,
    });
    return response;

  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Unauthorized" },
      { status: 401 },
    );
  }
}
