import { NextRequest, NextResponse } from "next/server";

import { env } from "@/lib/env";
import { getSessionFromRequest } from "@/lib/session";

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const session = getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const cleanPath = path.map((part) => part.replace(/^\/+|\/+$/g, "")).filter(Boolean).join("/");
  const targetUrl = `${env.backendBaseUrl}/${cleanPath}${request.nextUrl.search || ""}`;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }

  const method = request.method.toUpperCase();
  const init: RequestInit = {
    method,
    headers,
    cache: "no-store",
  };

  if (!["GET", "HEAD"].includes(method)) {
    const bodyText = await request.text();
    if (bodyText) {
      init.body = bodyText;
    }
  }

  const upstream = await fetch(targetUrl, init);
  const responseHeaders = new Headers();
  const upstreamContentType = upstream.headers.get("content-type");
  if (upstreamContentType) {
    responseHeaders.set("content-type", upstreamContentType);
  }
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path);
}
