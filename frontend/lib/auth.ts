// HMAC-signed httpOnly cookie. Uses Web Crypto API so it works in both
// Edge (middleware) and Node (route handlers) runtimes.

const SECRET = process.env.AUTH_SECRET || "dev-secret";
const COOKIE_NAME = "salesos_auth";
const MAX_AGE_S = 60 * 60 * 8; // 8 hours

function b64urlEncode(bytes: Uint8Array): string {
  let s = "";
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlDecodeToString(s: string): string {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  return atob(s);
}

async function hmacHex(payload: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(payload));
  const bytes = new Uint8Array(sig);
  let hex = "";
  for (let i = 0; i < bytes.length; i++) hex += bytes[i].toString(16).padStart(2, "0");
  return hex;
}

export async function makeToken(email: string): Promise<string> {
  const exp = Math.floor(Date.now() / 1000) + MAX_AGE_S;
  const payload = `${email}|${exp}`;
  const sig = await hmacHex(payload);
  const enc = new TextEncoder().encode(`${payload}|${sig}`);
  return b64urlEncode(enc);
}

function timingSafeEqualStr(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function verifyToken(token: string | undefined): Promise<{ email: string } | null> {
  if (!token) return null;
  try {
    const decoded = b64urlDecodeToString(token);
    const parts = decoded.split("|");
    if (parts.length !== 3) return null;
    const [email, expStr, sig] = parts;
    const expected = await hmacHex(`${email}|${expStr}`);
    if (!timingSafeEqualStr(sig, expected)) return null;
    if (Number(expStr) < Math.floor(Date.now() / 1000)) return null;
    return { email };
  } catch {
    return null;
  }
}

export const AUTH_COOKIE_NAME = COOKIE_NAME;
export const AUTH_MAX_AGE_S = MAX_AGE_S;
