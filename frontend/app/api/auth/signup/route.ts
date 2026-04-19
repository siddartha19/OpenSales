import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE_NAME, AUTH_MAX_AGE_S, makeToken } from "@/lib/auth";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const { name, email, password } = await req.json().catch(() => ({}));

  if (!name || !email || !password) {
    return NextResponse.json(
      { error: "Name, email, and password are required" },
      { status: 400 }
    );
  }

  try {
    const backendRes = await fetch(`${BACKEND_URL}/api/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });

    if (!backendRes.ok) {
      const data = await backendRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: data.detail || "Signup failed" },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();

    // Auto-login after signup: set auth cookie
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
    return NextResponse.json(
      { error: "Could not reach the server. Please try again." },
      { status: 503 }
    );
  }
}
