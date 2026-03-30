import { NextResponse } from "next/server";

import { env } from "@/lib/env";
import { getSessionUser } from "@/lib/session";

export async function GET() {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const response = await fetch(`${env.backendBaseUrl}/api/drafts`, {
    cache: "no-store",
  });
  const body = await response.json().catch(() => []);
  return NextResponse.json(body, { status: response.status });
}
