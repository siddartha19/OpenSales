"use client";

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`bg-stone-200/60 rounded animate-pulse ${className}`}
      aria-hidden="true"
    />
  );
}

export function PageHeaderSkeleton() {
  return (
    <header className="border-b border-border bg-white">
      <div className="max-w-6xl mx-auto px-6 py-4">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-56 mt-2" />
      </div>
    </header>
  );
}

export function MetricCardSkeleton() {
  return (
    <div className="card">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-7 w-16 mt-2" />
      <Skeleton className="h-3 w-12 mt-2" />
    </div>
  );
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <section className="card">
      <Skeleton className="h-5 w-32 mb-4" />
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-full" />
        ))}
      </div>
    </section>
  );
}

export function HomePageSkeleton() {
  return (
    <div role="status" aria-label="Loading dashboard">
      <PageHeaderSkeleton />
      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <MetricCardSkeleton key={i} />
          ))}
        </div>
        <CardSkeleton rows={6} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CardSkeleton rows={3} />
          <CardSkeleton rows={3} />
        </div>
      </div>
      <span className="sr-only">Loading dashboard…</span>
    </div>
  );
}

export function ListPageSkeleton({ title = "Loading", rowCount = 5 }: { title?: string; rowCount?: number }) {
  return (
    <div role="status" aria-label={title}>
      <PageHeaderSkeleton />
      <div className="max-w-5xl mx-auto px-6 py-6 space-y-4">
        <div className="flex gap-2">
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-7 w-20" />
          <Skeleton className="h-7 w-16" />
        </div>
        <div className="space-y-2">
          {Array.from({ length: rowCount }).map((_, i) => (
            <div key={i} className="card flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-3 w-64 mt-2" />
              </div>
              <Skeleton className="h-5 w-12" />
            </div>
          ))}
        </div>
      </div>
      <span className="sr-only">{title}…</span>
    </div>
  );
}

export function CRMSkeleton() {
  return (
    <div role="status" aria-label="Loading CRM" className="flex h-screen overflow-hidden">
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <header className="border-b border-border bg-white shrink-0">
          <div className="px-6 py-4 flex items-center justify-between">
            <div>
              <Skeleton className="h-7 w-24" />
              <Skeleton className="h-4 w-56 mt-2" />
            </div>
            <div className="flex gap-1">
              <Skeleton className="h-9 w-16" />
              <Skeleton className="h-9 w-16" />
              <Skeleton className="h-9 w-16" />
            </div>
          </div>
        </header>
        <div className="flex-1 overflow-auto">
          <div className="px-6 py-4 space-y-4">
            <div className="flex gap-3">
              <Skeleton className="h-9 w-64" />
              <Skeleton className="h-9 w-32" />
              <Skeleton className="h-9 w-32" />
            </div>
            <div className="card space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          </div>
        </div>
      </div>
      <span className="sr-only">Loading CRM…</span>
    </div>
  );
}
