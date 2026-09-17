import { CheckCircle2, Filter, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Analytics, Ticket } from "../types";
import { Badge, priorityVariant } from "./ui/Badge";

export function TicketsPage() {
  const { token } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [search, setSearch] = useState("");
  const [unitFilter, setUnitFilter] = useState("Tümü");
  const [statusFilter, setStatusFilter] = useState("Tümü");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Ticket | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    const [rows, stats] = await Promise.all([
      api.tickets(token),
      api.analytics(token),
    ]);
    setTickets(rows);
    setAnalytics(stats);
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    return tickets.filter((t) => {
      const unitOk =
        unitFilter === "Tümü" ||
        (t.birim_label ?? "").toLowerCase() === unitFilter.toLowerCase();
      const statusOk =
        statusFilter === "Tümü" ||
        (statusFilter === "Açık" && t.status !== "resolved") ||
        (statusFilter === "Çözüldü" && t.status === "resolved");
      const searchOk =
        !search.trim() ||
        JSON.stringify(t).toLowerCase().includes(search.toLowerCase());
      return unitOk && statusOk && searchOk;
    });
  }, [tickets, unitFilter, statusFilter, search]);

  async function resolve(id: string) {
    if (!token) return;
    setBusy(true);
    try {
      await api.resolveTicket(token, id);
      await refresh();
      setSelected(null);
    } finally {
      setBusy(false);
    }
  }

  const stats = [
    { label: "Toplam", value: analytics?.total_tickets ?? 0, color: "text-slate-900" },
    { label: "Açık", value: analytics?.open ?? 0, color: "text-blue-600" },
    { label: "Çözülen", value: analytics?.resolved ?? 0, color: "text-emerald-600" },
    {
      label: "AI Başarı",
      value: analytics?.feedback.total_feedback
        ? `%${analytics.feedback.overall_success_rate.toFixed(0)}`
        : "—",
      color: "text-slate-900",
    },
  ];

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto bg-surface-muted p-6">
      {/* KPI */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map(({ label, value, color }) => (
          <div key={label} className="card p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {label}
            </p>
            <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="card overflow-hidden">
        {/* Filtre bar */}
        <div className="flex flex-wrap items-center gap-3 border-b border-surface-border px-5 py-4">
          <Filter className="h-4 w-4 text-slate-400" />
          <select
            className="input-field !w-auto !py-1.5 text-sm"
            value={unitFilter}
            onChange={(e) => setUnitFilter(e.target.value)}
          >
            {["Tümü", "Bilgi Teknolojileri", "İdari İşler", "İnsan Kaynakları", "Finans"].map(
              (u) => (
                <option key={u}>{u}</option>
              ),
            )}
          </select>
          <select
            className="input-field !w-auto !py-1.5 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            {["Tümü", "Açık", "Çözüldü"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <div className="relative flex-1 min-w-[200px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className="input-field !py-1.5 pl-9 text-sm"
              placeholder="Bilet no, konu veya metin ara..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button type="button" className="btn-secondary !py-1.5" onClick={() => void refresh()}>
            <RefreshCw className="h-4 w-4" />
            Yenile
          </button>
          <span className="ml-auto text-sm text-slate-500">
            {filtered.length} kayıt
          </span>
        </div>

        {/* Tablo */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="px-5 py-3">Bilet No</th>
                <th className="px-5 py-3">Durum</th>
                <th className="px-5 py-3">Öncelik</th>
                <th className="px-5 py-3">Birim</th>
                <th className="px-5 py-3">Konu</th>
                <th className="px-5 py-3">Tarih</th>
                <th className="px-5 py-3">İşlem</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-400">
                    Kriterlere uygun bilet bulunamadı.
                  </td>
                </tr>
              ) : (
                [...filtered].reverse().map((ticket) => (
                  <tr
                    key={ticket.id}
                    className="cursor-pointer transition hover:bg-slate-50"
                    onClick={() => setSelected(ticket)}
                  >
                    <td className="px-5 py-3.5 font-mono text-xs font-semibold text-brand-600">
                      {ticket.id}
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge variant={ticket.status === "resolved" ? "resolved" : "open"}>
                        {ticket.status === "resolved" ? "Çözüldü" : "Açık"}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge variant={priorityVariant(ticket.priority ?? ticket.urgency)}>
                        {ticket.priority ?? ticket.urgency ?? "Orta"}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5 text-slate-600">
                      {ticket.birim_label ?? "—"}
                    </td>
                    <td className="max-w-xs truncate px-5 py-3.5 text-slate-900">
                      {ticket.customer_ask ?? ticket.path_label ?? "—"}
                    </td>
                    <td className="whitespace-nowrap px-5 py-3.5 text-slate-500">
                      {(ticket.created_at ?? "").slice(0, 16).replace("T", " ")}
                    </td>
                    <td className="px-5 py-3.5">
                      {ticket.status !== "resolved" ? (
                        <button
                          type="button"
                          className="btn-secondary !px-2.5 !py-1.5 !text-xs"
                          disabled={busy}
                          onClick={(e) => {
                            e.stopPropagation();
                            void resolve(ticket.id);
                          }}
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Kapat
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detay drawer */}
      {selected ? (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/20"
          onClick={() => setSelected(null)}
        >
          <div
            className="h-full w-full max-w-md overflow-y-auto bg-white shadow-panel"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-surface-border px-6 py-5">
              <p className="font-mono text-sm font-semibold text-brand-600">{selected.id}</p>
              <h3 className="mt-1 text-lg font-semibold text-slate-900">
                {selected.path_label ?? "Talep Detayı"}
              </h3>
              <div className="mt-3 flex gap-2">
                <Badge variant={selected.status === "resolved" ? "resolved" : "open"}>
                  {selected.status === "resolved" ? "Çözüldü" : "Açık"}
                </Badge>
                <Badge variant={priorityVariant(selected.priority ?? selected.urgency)}>
                  {selected.priority ?? selected.urgency ?? "Orta"}
                </Badge>
              </div>
            </div>
            <div className="space-y-5 px-6 py-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Talep
                </p>
                <p className="mt-1 text-sm text-slate-700">{selected.customer_ask}</p>
              </div>
              {selected.slots && Object.keys(selected.slots).length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Toplanan Alanlar
                  </p>
                  <dl className="mt-2 space-y-2">
                    {Object.entries(selected.slots)
                      .filter(([, v]) => v)
                      .map(([k, v]) => (
                        <div key={k} className="flex justify-between gap-4 text-sm">
                          <dt className="text-slate-500">{k.replace(/_/g, " ")}</dt>
                          <dd className="font-medium text-slate-900">{v}</dd>
                        </div>
                      ))}
                  </dl>
                </div>
              ) : null}
              {selected.status !== "resolved" ? (
                <button
                  type="button"
                  className="btn-primary w-full"
                  disabled={busy}
                  onClick={() => void resolve(selected.id)}
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Çözüldü Olarak İşaretle
                </button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
