"use client";

import { useEffect, useState } from "react";
import { useDocumentTitle } from "@/lib/useDocumentTitle";

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  created_at: string;
}

export default function AdminPage() {
  useDocumentTitle("Admin");
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  async function fetchUsers() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/api/proxy/users");
      if (!r.ok) throw new Error("Failed to fetch users");
      const data = await r.json();
      setUsers(data.users || []);
    } catch (e: any) {
      setError(e?.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  function formatDate(iso: string) {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  return (
    <div>
      <header className="border-b border-border bg-white">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
          <p className="text-sm text-stone-500 mt-1.5">
            All registered users on SalesOS
          </p>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        {/* Stats bar */}
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <div className="text-2xl font-bold text-accent">{users.length}</div>
            <div className="text-xs text-stone-500 mt-1">Total Users</div>
          </div>
          <div className="card text-center">
            <div className="text-2xl font-bold text-accent">
              {users.filter((u) => u.role === "admin").length}
            </div>
            <div className="text-xs text-stone-500 mt-1">Admins</div>
          </div>
          <div className="card text-center">
            <div className="text-2xl font-bold text-accent">
              {users.filter((u) => u.role === "user").length}
            </div>
            <div className="text-xs text-stone-500 mt-1">Regular Users</div>
          </div>
        </div>

        {/* Users table */}
        <div className="card overflow-hidden p-0">
          {loading ? (
            <div className="p-8 text-center text-stone-400">Loading users...</div>
          ) : error ? (
            <div className="p-8 text-center">
              <div className="text-danger text-sm mb-3">{error}</div>
              <button onClick={fetchUsers} className="btn btn-primary text-sm">
                Retry
              </button>
            </div>
          ) : users.length === 0 ? (
            <div className="p-8 text-center text-stone-400">
              No users registered yet.
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-stone-50">
                  <th className="text-left text-xs font-medium text-stone-500 uppercase tracking-wider px-4 py-3">
                    Name
                  </th>
                  <th className="text-left text-xs font-medium text-stone-500 uppercase tracking-wider px-4 py-3">
                    Email
                  </th>
                  <th className="text-left text-xs font-medium text-stone-500 uppercase tracking-wider px-4 py-3">
                    Role
                  </th>
                  <th className="text-left text-xs font-medium text-stone-500 uppercase tracking-wider px-4 py-3">
                    Signed Up
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-border last:border-b-0 hover:bg-stone-50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-accent text-white flex items-center justify-center font-bold text-sm">
                          {user.name.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-sm font-medium text-ink">
                          {user.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-stone-600">
                      {user.email}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
                          user.role === "admin"
                            ? "bg-accent/10 text-accent"
                            : "bg-stone-100 text-stone-600"
                        }`}
                      >
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-stone-500">
                      {formatDate(user.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
