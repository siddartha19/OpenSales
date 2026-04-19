import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE_NAME, AUTH_MAX_AGE_S, makeToken } from "@/lib/auth";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const { email, password } = await req.json().catch(() => ({}));
  if (!email || !password) {
    return NextResponse.json({ error: "Email and password are required" }, { status: 400 });
  }

  // Validate against backend users DB
  try {
    const backendRes = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!backendRes.ok) {
      return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
    }

    const data = await backendRes.json();
    const token = await makeToken(email);
    const res = NextResponse.json({ ok: true, user: data.user });
    res.cookies.set(AUTH_COOKIE_NAME, token, {
      httpOnly: true,
      sameSite: "lax",
      maxAge: AUTH_MAX_AGE_S,
      path: "/",
    });
    return res;
  } catch {
    // Fallback: if backend is unreachable, use env-based auth
    const wantEmail = process.env.AUTH_EMAIL || "hr@alerahq.com";
    const wantPass = process.env.AUTH_PASSWORD || "Admin@123";
    if (email !== wantEmail || password !== wantPass) {
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
}
