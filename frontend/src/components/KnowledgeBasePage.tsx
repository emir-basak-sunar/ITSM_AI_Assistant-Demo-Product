import { Search, ThumbsDown, ThumbsUp } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { SolutionRow } from "../types";

type KbFilter = "all" | "sap" | "itsm";

export function KnowledgeBasePage() {
  const { token } = useAuth();
  const [solutions, setSolutions] = useState<SolutionRow[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<KbFilter>("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    setSolutions(await api.solutions(token));
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    let rows = solutions;
    if (filter === "sap") {
      rows = rows.filter((s) => s.birim_label === "SAP ERP");
    } else if (filter === "itsm") {
      rows = rows.filter((s) => s.birim_label !== "SAP ERP");
    }
    if (!search.trim()) return rows;
    const q = search.toLowerCase();
    return rows.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.surec_label.toLowerCase().includes(q) ||
        s.birim_label.toLowerCase().includes(q) ||
        s.modul_label.toLowerCase().includes(q) ||
        (s.module_overview ?? "").toLowerCase().includes(q),
    );
  }, [solutions, search, filter]);

  const grouped = useMemo(() => {
    const map = new Map<string, SolutionRow[]>();
    for (const row of filtered) {
      const key =
        row.birim_label === "SAP ERP"
          ? `SAP ERP — ${row.modul_label}`
          : row.birim_label || "Diğer";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(row);
    }
    const entries = [...map.entries()];
    entries.sort(([a], [b]) => {
      const aSap = a.startsWith("SAP");
      const bSap = b.startsWith("SAP");
      if (aSap && !bSap) return -1;
      if (!aSap && bSap) return 1;
      return a.localeCompare(b, "tr");
    });
    return entries;
  }, [filtered]);

  async function feedback(id: string, helpful: boolean) {
    if (!token) return;
    await api.feedback(token, id, helpful);
    await refresh();
  }

  const sapCount = solutions.filter((s) => s.birim_label === "SAP ERP").length;

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto bg-surface-muted p-6">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-slate-900">Bilgi Bankası</h2>
        <p className="text-sm text-slate-500">
          Kurumsal ITSM çözümleri ve SAP ERP modül rehberleri
        </p>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="flex rounded-lg border border-surface-border bg-white p-1">
          {(
            [
              ["all", "Tümü"],
              ["sap", `SAP ERP (${sapCount})`],
              ["itsm", "Kurumsal ITSM"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setFilter(id)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                filter === id
                  ? "bg-brand-600 text-white"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="relative min-w-[220px] flex-1 max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="input-field pl-9"
            placeholder="Modül, işlem kodu veya konu ara..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <span className="text-sm text-slate-500">{filtered.length} kayıt</span>
      </div>

      <div className="space-y-6">
        {grouped.length === 0 ? (
          <p className="card py-12 text-center text-sm text-slate-400">
            Arama kriterlerine uygun kayıt bulunamadı.
          </p>
        ) : (
          grouped.map(([group, items]) => (
            <div key={group}>
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
                {group.startsWith("SAP") ? (
                  <span className="rounded bg-brand-100 px-2 py-0.5 text-xs font-bold text-brand-700">
                    SAP
                  </span>
                ) : null}
                {group}
              </h3>
              <div className="space-y-2">
                {items.map((item) => {
                  const open = expanded === item.id;
                  return (
                    <div key={item.id} className="card overflow-hidden">
                      <button
                        type="button"
                        className="flex w-full items-center justify-between px-5 py-4 text-left transition hover:bg-slate-50"
                        onClick={() => setExpanded(open ? null : item.id)}
                      >
                        <div>
                          <p className="font-medium text-slate-900">{item.title}</p>
                          <p className="mt-0.5 text-xs text-slate-500">
                            {item.surec_label} · {item.talep_turu}
                          </p>
                        </div>
                        <span className="shrink-0 text-xs text-slate-400">
                          {item.stats.rating_display}
                        </span>
                      </button>
                      {open ? (
                        <div className="space-y-4 border-t border-surface-border px-5 py-4 text-sm text-slate-600">
                          {item.module_overview ? (
                            <div>
                              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                                Modül Özeti
                              </p>
                              <p className="leading-relaxed">{item.module_overview}</p>
                            </div>
                          ) : null}

                          {item.common_transactions?.length ? (
                            <div>
                              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                                Sık Kullanılan İşlem Kodları (T-Code)
                              </p>
                              <ul className="grid gap-1 sm:grid-cols-2">
                                {item.common_transactions.map((tx) => (
                                  <li
                                    key={tx}
                                    className="rounded bg-slate-50 px-2 py-1 font-mono text-xs text-slate-700"
                                  >
                                    {tx}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          ) : null}

                          {item.common_issues?.length ? (
                            <div>
                              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                                Sık Karşılaşılan Sorunlar
                              </p>
                              <ul className="list-disc space-y-1 pl-5">
                                {item.common_issues.map((issue) => (
                                  <li key={issue}>{issue}</li>
                                ))}
                              </ul>
                            </div>
                          ) : null}

                          <div>
                            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                              Çözüm Adımları
                            </p>
                            <ol className="list-decimal space-y-2 pl-5">
                              {item.steps.map((step) => (
                                <li key={step}>{step}</li>
                              ))}
                            </ol>
                          </div>

                          <p className="text-xs text-slate-400">
                            Zorunlu alanlar:{" "}
                            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
                              {item.zorunlu_alanlar.join(", ")}
                            </code>
                          </p>

                          <div className="flex gap-2 pt-1">
                            <button
                              type="button"
                              className="btn-secondary !text-xs"
                              onClick={() => void feedback(item.id, true)}
                            >
                              <ThumbsUp className="h-3.5 w-3.5" />
                              Faydalı
                            </button>
                            <button
                              type="button"
                              className="btn-secondary !text-xs"
                              onClick={() => void feedback(item.id, false)}
                            >
                              <ThumbsDown className="h-3.5 w-3.5" />
                              Geliştir
                            </button>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
