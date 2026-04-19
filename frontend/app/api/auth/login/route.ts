import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE_NAME, AUTH_MAX_AGE_S, makeToken } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const { email, password } = await req.json().catch(() => ({}));
  const wantEmail = process.env.AUTH_EMAIL || "hr@alerahq.com";
  const wantPass = process.env.AUTH_PASSWORD || "Admin@123";
  if (!email || !password || email !== wantEmail || password !== wantPass) {
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }
  const token = await makeToken(email);
  const res = NextResponse.json({ ok: true });
  res.cookies.set(AUTH_COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: AUTH_MAX_AGE_S,
    path: "/",
  });
  return res;
}
