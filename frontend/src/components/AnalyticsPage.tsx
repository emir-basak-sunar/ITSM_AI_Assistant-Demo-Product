import { Play, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Analytics, JobRow } from "../types";
import { Badge } from "./ui/Badge";

export function AnalyticsPage() {
  const { token } = useAuth();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [jobMessage, setJobMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    const [stats, jobRows] = await Promise.all([
      api.analytics(token),
      api.jobs(token),
    ]);
    setAnalytics(stats);
    setJobs(jobRows);
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function runJobs() {
    if (!token) return;
    setBusy(true);
    setJobMessage(null);
    try {
      const result = await api.runJobs(token);
      await refresh();
      setJobMessage({
        type: "ok",
        text:
          result.count > 0
            ? `${result.count} rapor başarıyla oluşturuldu ve arşivlendi.`
            : "Rapor oluşturuldu.",
      });
    } catch (err) {
      setJobMessage({
        type: "err",
        text: err instanceof Error ? err.message : "JOB çalıştırılamadı.",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto bg-surface-muted p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Performans Özeti</h2>
          <p className="text-sm text-slate-500">Bilet ve self-service metrikleri</p>
        </div>
        <button type="button" className="btn-secondary" onClick={() => void refresh()}>
          <RefreshCw className="h-4 w-4" />
          Yenile
        </button>
      </div>

      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Toplam Bilet", value: analytics?.total_tickets ?? 0 },
          { label: "Açık", value: analytics?.open ?? 0 },
          { label: "Çözülen", value: analytics?.resolved ?? 0 },
          {
            label: "AI Başarı Oranı",
            value: analytics?.feedback.total_feedback
              ? `%${analytics.feedback.overall_success_rate.toFixed(0)}`
              : "Veri yok",
          },
        ].map(({ label, value }) => (
          <div key={label} className="card p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {label}
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
          </div>
        ))}
      </div>

      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-slate-900">Günlük Rapor JOB</h3>
            <p className="mt-0.5 text-sm text-slate-500">
              Kuyruktaki rapor komutlarını çalıştır
            </p>
          </div>
          <button type="button" className="btn-primary" disabled={busy} onClick={() => void runJobs()}>
            <Play className="h-4 w-4" />
            {busy ? "Çalışıyor..." : "JOB Çalıştır"}
          </button>
        </div>

        {jobMessage ? (
          <div
            className={`mt-4 rounded-lg px-4 py-3 text-sm ${
              jobMessage.type === "ok"
                ? "border border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border border-red-200 bg-red-50 text-red-800"
            }`}
          >
            {jobMessage.text}
          </div>
        ) : null}

        <div className="mt-6 space-y-3">
          {jobs.length === 0 ? (
            <p className="rounded-lg bg-slate-50 py-8 text-center text-sm text-slate-400">
              Henüz rapor komutu yok. Asistan üzerinden rapor talep edin.
            </p>
          ) : (
            [...jobs].reverse().map((job) => (
              <details key={job.id} className="rounded-lg border border-surface-border bg-slate-50">
                <summary className="flex cursor-pointer items-center gap-3 px-4 py-3 text-sm font-medium text-slate-700">
                  <span className="font-mono text-xs text-brand-600">{job.id}</span>
                  <span className="flex-1 truncate">{job.command}</span>
                  <Badge variant={job.status === "sent" ? "resolved" : "open"}>
                    {job.status === "sent" ? "Tamamlandı" : "Kuyrukta"}
                  </Badge>
                </summary>
                {job.result ? (
                  <div className="border-t border-surface-border px-4 py-3 text-sm text-slate-600">
                    <ReactMarkdown>{job.result}</ReactMarkdown>
                  </div>
                ) : null}
              </details>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
