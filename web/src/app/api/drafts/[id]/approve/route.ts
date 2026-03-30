import { NextResponse } from "next/server";

import { env } from "@/lib/env";
import { getSessionFromRequest } from "@/lib/session";

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const session = getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const { id } = await context.params;
  const endpoint = `${env.backendBaseUrl}/api/drafts/${id}/approve`;
  const response = await fetch(endpoint, { method: "POST", cache: "no-store" });
  const payload = await response.json().catch(() => ({}));

  return NextResponse.json(payload, { status: response.status });
}
