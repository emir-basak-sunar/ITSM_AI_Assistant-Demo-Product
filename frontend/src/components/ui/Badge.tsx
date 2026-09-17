import type { ReactNode } from "react";

type BadgeVariant = "open" | "resolved" | "critical" | "high" | "medium" | "low" | "neutral";

const styles: Record<BadgeVariant, string> = {
  open: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-600/20",
  resolved: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20",
  critical: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20",
  high: "bg-orange-50 text-orange-700 ring-1 ring-inset ring-orange-600/20",
  medium: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20",
  low: "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-500/20",
  neutral: "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-500/10",
};

export function priorityVariant(priority?: string): BadgeVariant {
  const p = (priority ?? "").toLowerCase();
  if (p.includes("kritik")) return "critical";
  if (p.includes("yüksek") || p.includes("yuksek") || p === "high") return "high";
  if (p.includes("düşük") || p.includes("dusuk") || p === "low") return "low";
  if (p.includes("orta") || p === "medium") return "medium";
  return "neutral";
}

export function Badge({
  children,
  variant = "neutral",
}: {
  children: ReactNode;
  variant?: BadgeVariant;
}) {
  return <span className={`badge ${styles[variant]}`}>{children}</span>;
}
