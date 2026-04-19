"use client";

export default function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="card">
      <div className="label mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${accent ? "text-accent" : ""}`}>{value}</div>
      {sub && <div className="text-xs text-stone-500 mt-0.5">{sub}</div>}
    </div>
  );
}
