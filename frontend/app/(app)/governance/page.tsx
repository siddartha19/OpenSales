"use client";

import { useEffect, useState } from "react";
import type { CompanyInfo, ICPProfile } from "@/types";

const EMPTY_COMPANY: CompanyInfo = {
  name: "",
  domain: "",
  industry: "",
  description: "",
  team_size: "",
  meeting_link: "",
};

export default function GovernancePage() {
  const [company, setCompany] = useState<CompanyInfo>(EMPTY_COMPANY);
  const [icps, setIcps] = useState<ICPProfile[]>([]);
  const [newIcp, setNewIcp] = useState({ name: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [editingIcp, setEditingIcp] = useState<string | null>(null);

  useEffect(() => {
    loadGovernance();
  }, []);

  async function loadGovernance() {
    try {
      const r = await fetch("/api/proxy/governance");
      const j = await r.json();
      if (j.company) setCompany(j.company);
      if (j.icps) setIcps(j.icps);
    } catch {}
  }

  async function saveCompany() {
    setSaving(true);
    setSaved(false);
    try {
      await fetch("/api/proxy/governance/company", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(company),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {} finally {
      setSaving(false);
    }
  }

  async function addIcp() {
    if (!newIcp.name.trim()) return;
    try {
      const r = await fetch("/api/proxy/governance/icps", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newIcp),
      });
      const j = await r.json();
      if (j.icp) setIcps((prev) => [j.icp, ...prev]);
      setNewIcp({ name: "", description: "" });
    } catch {}
  }

  async function deleteIcp(id: string) {
    try {
      await fetch(`/api/proxy/governance/icps/${id}`, { method: "DELETE" });
      setIcps((prev) => prev.filter((i) => i.id !== id));
    } catch {}
  }

  async function updateIcp(id: string, data: { name: string; description: string }) {
    try {
      const r = await fetch(`/api/proxy/governance/icps/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const j = await r.json();
      if (j.icp) setIcps((prev) => prev.map((i) => (i.id === id ? j.icp : i)));
      setEditingIcp(null);
    } catch {}
  }

  return (
    <div>
      <header className="border-b border-border bg-white">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <h1 className="text-xl font-semibold">Governance</h1>
          <p className="text-sm text-stone-500 mt-0.5">Company info, ICPs, and sender settings</p>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        {/* Company Info */}
        <section className="card">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="font-semibold text-lg">Company Information</h2>
            <button
              onClick={saveCompany}
              disabled={saving}
              className="btn btn-primary"
            >
              {saving ? "Saving…" : saved ? "Saved" : "Save Changes"}
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Company Name</label>
              <input
                className="input mt-1"
                value={company.name}
                onChange={(e) => setCompany({ ...company, name: e.target.value })}
                placeholder="Acme Corp"
              />
            </div>
            <div>
              <label className="label">Domain</label>
              <input
                className="input mt-1"
                value={company.domain}
                onChange={(e) => setCompany({ ...company, domain: e.target.value })}
                placeholder="acme.com"
              />
            </div>
            <div>
              <label className="label">Industry</label>
              <input
                className="input mt-1"
                value={company.industry}
                onChange={(e) => setCompany({ ...company, industry: e.target.value })}
                placeholder="SaaS / AI"
              />
            </div>
            <div>
              <label className="label">Team Size</label>
              <input
                className="input mt-1"
                value={company.team_size}
                onChange={(e) => setCompany({ ...company, team_size: e.target.value })}
                placeholder="10-50"
              />
            </div>
            <div className="md:col-span-2">
              <label className="label">Description</label>
              <textarea
                className="textarea mt-1 h-20"
                value={company.description}
                onChange={(e) => setCompany({ ...company, description: e.target.value })}
                placeholder="What your company does…"
              />
            </div>
            <div className="md:col-span-2">
              <label className="label">Meeting / Calendly Link</label>
              <input
                className="input mt-1"
                value={company.meeting_link}
                onChange={(e) => setCompany({ ...company, meeting_link: e.target.value })}
                placeholder="https://calendly.com/you/30min"
              />
              <p className="text-xs text-stone-400 mt-1">Used in follow-up meeting request emails</p>
            </div>
          </div>
        </section>

        {/* ICPs */}
        <section className="card">
          <h2 className="font-semibold text-lg mb-4">Ideal Customer Profiles</h2>

          {/* Add new ICP */}
          <div className="border border-dashed border-stone-300 rounded-lg p-4 mb-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="label">ICP Name</label>
                <input
                  className="input mt-1"
                  value={newIcp.name}
                  onChange={(e) => setNewIcp({ ...newIcp, name: e.target.value })}
                  placeholder="Series A AI Founders"
                />
              </div>
              <div className="md:col-span-2">
                <label className="label">Description / Criteria</label>
                <div className="flex gap-2 mt-1">
                  <input
                    className="input flex-1"
                    value={newIcp.description}
                    onChange={(e) => setNewIcp({ ...newIcp, description: e.target.value })}
                    placeholder="Indian AI startup founders, Series A or earlier, building AI agent products"
                    onKeyDown={(e) => e.key === "Enter" && addIcp()}
                  />
                  <button
                    onClick={addIcp}
                    disabled={!newIcp.name.trim()}
                    className="btn btn-primary shrink-0"
                  >
                    + Add ICP
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ICP list */}
          {icps.length === 0 ? (
            <p className="text-sm text-stone-400">No ICPs saved yet. Add one above to use in campaigns.</p>
          ) : (
            <div className="space-y-2">
              {icps.map((icp) => (
                <div
                  key={icp.id}
                  className="flex items-start justify-between gap-3 p-3 rounded-lg border border-border hover:bg-stone-50 transition"
                >
                  {editingIcp === icp.id ? (
                    <EditIcpRow
                      icp={icp}
                      onSave={(data) => updateIcp(icp.id, data)}
                      onCancel={() => setEditingIcp(null)}
                    />
                  ) : (
                    <>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm">{icp.name}</div>
                        <div className="text-sm text-stone-500 mt-0.5">{icp.description}</div>
                        <div className="text-xs text-stone-400 mt-1">
                          Created {new Date(icp.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={() => setEditingIcp(icp.id)}
                          className="text-xs text-stone-400 hover:text-accent px-2 py-1"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => deleteIcp(icp.id)}
                          className="text-xs text-stone-400 hover:text-danger px-2 py-1"
                        >
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function EditIcpRow({
  icp,
  onSave,
  onCancel,
}: {
  icp: ICPProfile;
  onSave: (data: { name: string; description: string }) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(icp.name);
  const [description, setDescription] = useState(icp.description);

  return (
    <div className="flex-1 space-y-2">
      <input className="input text-sm" value={name} onChange={(e) => setName(e.target.value)} />
      <input className="input text-sm" value={description} onChange={(e) => setDescription(e.target.value)} />
      <div className="flex gap-2">
        <button onClick={() => onSave({ name, description })} className="btn btn-primary text-xs">Save</button>
        <button onClick={onCancel} className="btn text-xs">Cancel</button>
      </div>
    </div>
  );
}
