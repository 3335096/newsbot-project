import { NextRequest, NextResponse } from "next/server";

import { clearSessionCookie, getSessionUser } from "@/lib/session";

export async function GET() {
  const user = await getSessionUser();
  return NextResponse.json({
    authenticated: Boolean(user),
    user,
  });
}

export async function DELETE(_request: NextRequest) {
  await clearSessionCookie();
  return NextResponse.json({ ok: true });
}
