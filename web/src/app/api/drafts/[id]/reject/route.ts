import { NextRequest, NextResponse } from "next/server";

import { env } from "@/lib/env";
import { getSessionFromRequest } from "@/lib/session";

type RejectPayload = {
  reason?: string;
};

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const session = getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const { id } = await context.params;

  let payload: RejectPayload;
  try {
    payload = (await request.json()) as RejectPayload;
  } catch {
    return NextResponse.json({ error: "Invalid JSON payload" }, { status: 400 });
  }

  const reason = (payload.reason ?? "").trim();
  if (!reason) {
    return NextResponse.json({ error: "Reason is required" }, { status: 400 });
  }

  const apiResponse = await fetch(`${env.backendBaseUrl}/api/drafts/${id}/reject`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ reason }),
    cache: "no-store",
  });

  const data = await apiResponse.json().catch(() => ({}));
  if (!apiResponse.ok) {
    return NextResponse.json(
      { detail: data.detail ?? "Failed to reject draft" },
      { status: apiResponse.status },
    );
  }

  return NextResponse.json(data);
}
