"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import type { SessionInfo } from "@/types";

const NAV_ITEMS = [
  { label: "Home", href: "/", icon: "⌂" },
  { label: "Governance", href: "/governance", icon: "◈" },
  { label: "CRM", href: "/crm", icon: "◫" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [campaignsOpen, setCampaignsOpen] = useState(true);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchSessions();
  }, []);

  async function fetchSessions() {
    try {
      const r = await fetch("/api/proxy/sessions");
      const j = await r.json();
      setSessions(j.sessions || []);
    } catch {}
  }

  async function createSession() {
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    try {
      await fetch("/api/proxy/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      setNewName("");
      await fetchSessions();
    } catch {} finally {
      setCreating(false);
    }
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  const isCampaignActive = pathname.startsWith("/campaigns");

  return (
    <aside className="w-60 min-w-[15rem] border-r border-border bg-white flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-4 pt-4 pb-3 border-b border-border">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent text-white flex items-center justify-center font-bold text-sm">S</div>
          <span className="font-semibold text-[15px] tracking-tight">SalesOS</span>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-2">
        {/* Top nav items */}
        {NAV_ITEMS.slice(0, 2).map((item) => (
          <NavLink key={item.href} {...item} active={pathname === item.href} />
        ))}

        {/* Campaigns collapsible section */}
        <div className="mt-1">
          <button
            onClick={() => setCampaignsOpen(!campaignsOpen)}
            className={`w-full flex items-center justify-between px-4 py-2 text-sm hover:bg-stone-50 transition ${
              isCampaignActive ? "text-accent font-medium" : "text-stone-700"
            }`}
          >
            <span className="flex items-center gap-2.5">
              <span className="text-xs w-4 text-center opacity-60">◇</span>
              Campaigns
            </span>
            <span className="text-[10px] text-stone-400">{campaignsOpen ? "▾" : "▸"}</span>
          </button>

          {campaignsOpen && (
            <div className="ml-4 border-l border-stone-100">
              <Link
                href="/campaigns"
                className={`block px-4 py-1.5 text-sm hover:bg-stone-50 transition ${
                  pathname === "/campaigns" ? "text-accent font-medium bg-accentSoft/40" : "text-stone-600"
                }`}
              >
                View all ({sessions.length})
              </Link>
              {sessions.slice(0, 5).map((s) => (
                <Link
                  key={s.session_id}
                  href={`/campaigns/${s.session_id}`}
                  className={`block px-4 py-1.5 text-sm truncate hover:bg-stone-50 transition ${
                    pathname === `/campaigns/${s.session_id}` ? "text-accent font-medium bg-accentSoft/40" : "text-stone-500"
                  }`}
                  title={s.name}
                >
                  {s.name}
                </Link>
              ))}
              <div className="px-3 py-1.5">
                <div className="flex gap-1">
                  <input
                    className="input text-sm py-1 px-2 flex-1"
                    placeholder="New campaign…"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && createSession()}
                  />
                  <button
                    onClick={createSession}
                    disabled={creating || !newName.trim()}
                    className="text-accent text-sm font-semibold px-1.5 hover:bg-accentSoft rounded transition disabled:opacity-30"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Bottom nav items */}
        {NAV_ITEMS.slice(2).map((item) => (
          <NavLink key={item.href} {...item} active={pathname === item.href} />
        ))}
      </nav>

      {/* Logout */}
      <div className="p-3 border-t border-border">
        <button onClick={logout} className="btn btn-ghost text-stone-500 w-full text-sm justify-center">
          Logout
        </button>
      </div>
    </aside>
  );
}

function NavLink({ label, href, icon, active }: { label: string; href: string; icon: string; active: boolean }) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2.5 px-4 py-2 text-sm transition ${
        active
          ? "text-accent font-medium bg-accentSoft/40 border-r-2 border-accent"
          : "text-stone-700 hover:bg-stone-50"
      }`}
    >
      <span className="text-xs w-4 text-center opacity-60">{icon}</span>
      {label}
    </Link>
  );
}
