import { NextResponse } from "next/server";

import { env } from "@/lib/env";
import { getSessionUser } from "@/lib/session";
import type { SourceOut } from "@/lib/types";

export async function GET() {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const response = await fetch(`${env.backendBaseUrl}/api/sources`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text().catch(() => "");
    return NextResponse.json(
      { detail: "Unable to load sources", details: message },
      { status: response.status },
    );
  }

  const payload = (await response.json()) as SourceOut[];
  return NextResponse.json(payload);
}
