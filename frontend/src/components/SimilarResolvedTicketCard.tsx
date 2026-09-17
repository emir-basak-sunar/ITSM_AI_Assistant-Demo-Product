import { CheckCircle2, MessageSquare, Ticket } from "lucide-react";
import type { SimilarResolvedTicket } from "../types";

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function SimilarResolvedTicketCard({ ticket }: { ticket: SimilarResolvedTicket }) {
  return (
    <div className="overflow-hidden rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white shadow-card">
      <div className="flex items-start justify-between gap-3 border-b border-emerald-100 bg-white/80 px-4 py-3">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
            <Ticket className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Benzer Çözülmüş Kayıt</p>
            <p className="text-xs text-slate-500">
              {ticket.id} · %{ticket.similarity_pct ?? "—"} benzerlik
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-800">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Çözüldü
        </span>
      </div>

      <div className="space-y-3 px-4 py-3">
        {ticket.path_label ? (
          <p className="text-xs text-slate-500">{ticket.path_label}</p>
        ) : null}

        <div className="rounded-lg bg-white px-3 py-2 ring-1 ring-emerald-100">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">İlk talep</p>
          <p className="mt-1 text-sm text-slate-800">{ticket.customer_ask}</p>
        </div>

        {ticket.resolution_summary ? (
          <div className="rounded-lg border border-emerald-100 bg-emerald-50/70 px-3 py-2">
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">Çözüm özeti</p>
            <p className="mt-1 text-sm text-emerald-900">{ticket.resolution_summary}</p>
          </div>
        ) : null}

        {ticket.messages && ticket.messages.length > 0 ? (
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-500">
              <MessageSquare className="h-3.5 w-3.5" />
              Kayıt mesajlaşması
            </div>
            <div className="max-h-56 space-y-2 overflow-y-auto rounded-lg bg-white p-3 ring-1 ring-surface-border">
              {ticket.messages.map((message, index) => {
                const isAgent = message.role === "agent";
                return (
                  <div
                    key={`${message.at}-${index}`}
                    className={`rounded-lg px-3 py-2 text-sm ${
                      isAgent
                        ? "bg-brand-50 text-brand-900 ring-1 ring-brand-100"
                        : "bg-slate-50 text-slate-800 ring-1 ring-surface-border"
                    }`}
                  >
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold">{isAgent ? "Destek" : "Kullanıcı"}</span>
                      <span className="text-[10px] text-slate-400">{formatDate(message.at)}</span>
                    </div>
                    <p className="leading-relaxed">{message.content}</p>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        <p className="text-[11px] text-slate-400">
          Çözüm: {formatDate(ticket.resolved_at || ticket.created_at)}
        </p>
      </div>
    </div>
  );
}
