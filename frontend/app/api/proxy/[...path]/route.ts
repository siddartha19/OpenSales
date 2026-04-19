// Generic proxy: forwards /api/proxy/<path> to BACKEND_URL/api/<path>.
// Extracts user email from the auth cookie and sends it as X-User-Email header.
import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE_NAME, verifyToken } from "@/lib/auth";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

async function forward(req: NextRequest, path: string[]) {
  const url = `${BACKEND}/api/${path.join("/")}${req.nextUrl.search}`;

  // Extract user email from auth cookie
  const token = req.cookies.get(AUTH_COOKIE_NAME)?.value;
  const session = await verifyToken(token);
  const userEmail = session?.email || "";

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (userEmail) {
    headers["X-User-Email"] = userEmail;
  }

  const init: RequestInit = {
    method: req.method,
    headers,
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }
  try {
    const r = await fetch(url, init);
    const text = await r.text();
    return new NextResponse(text, {
      status: r.status,
      headers: { "Content-Type": r.headers.get("Content-Type") || "application/json" },
    });
  } catch (e: any) {
    return NextResponse.json(
      { error: `Backend unreachable: ${e?.message || e}`, backend: BACKEND },
      { status: 502 }
    );
  }
}

export async function GET(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params.path);
}
export async function POST(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params.path);
}
export async function PUT(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params.path);
}
export async function DELETE(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params.path);
}
