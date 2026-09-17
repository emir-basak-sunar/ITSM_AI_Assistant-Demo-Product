import {
  BarChart3,
  BookOpen,
  Headphones,
  Ticket,
} from "lucide-react";
import { BtcLogo } from "../ui/BtcLogo";

export type PageId = "chat" | "tickets" | "analytics" | "kb";

const NAV: { id: PageId; label: string; icon: typeof Ticket }[] = [
  { id: "chat", label: "Destek Asistanı", icon: Headphones },
  { id: "tickets", label: "Biletler", icon: Ticket },
  { id: "analytics", label: "Raporlar", icon: BarChart3 },
  { id: "kb", label: "Bilgi Bankası", icon: BookOpen },
];

export function Sidebar({
  active,
  onNavigate,
}: {
  active: PageId;
  onNavigate: (page: PageId) => void;
}) {
  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-surface-border bg-white">
      <div className="flex h-16 items-center gap-3 border-b border-surface-border px-5">
        <BtcLogo className="h-9 w-auto shrink-0" />
        <div>
          <p className="text-sm font-bold text-slate-900">ITSM Desk</p>
          <p className="text-xs text-slate-500">Kurumsal Destek</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV.map(({ id, label, icon: Icon }) => {
          const selected = active === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onNavigate(id)}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                selected
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <Icon className={`h-4 w-4 ${selected ? "text-brand-600" : "text-slate-400"}`} />
              {label}
            </button>
          );
        })}
      </nav>

      <div className="border-t border-surface-border p-4">
        <p className="text-xs text-slate-400">ITSM AI Asistanı v2.0</p>
      </div>
    </aside>
  );
}
