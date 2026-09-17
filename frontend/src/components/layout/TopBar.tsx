import { Bell, LogOut, Search } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { BtcLogo } from "../ui/BtcLogo";
import type { PageId } from "./Sidebar";

const TITLES: Record<PageId, string> = {
  chat: "Destek Asistanı",
  tickets: "Bilet Yönetimi",
  analytics: "Raporlar & Analitik",
  kb: "Bilgi Bankası",
};

export function TopBar({ page }: { page: PageId }) {
  const { user, llmActive, llmProvider, logout } = useAuth();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-surface-border bg-white px-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">{TITLES[page]}</h1>
        <p className="text-xs text-slate-500">
          {llmActive ? `${llmProvider} aktif` : "Kural tabanlı mod aktif"}
        </p>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative hidden md:block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="input-field w-64 !py-2 pl-9"
            placeholder="Bilet veya konu ara..."
            readOnly
          />
        </div>

        <button type="button" className="btn-ghost relative !p-2" aria-label="Bildirimler">
          <Bell className="h-5 w-5 text-slate-500" />
        </button>

        <div className="flex items-center gap-3 border-l border-surface-border pl-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
            {(user?.name ?? "K").charAt(0).toUpperCase()}
          </div>
          <div className="hidden text-right sm:block">
            <p className="text-sm font-medium text-slate-900">{user?.name}</p>
            <p className="text-xs text-slate-500">{user?.email}</p>
          </div>
          <button type="button" className="btn-ghost !p-2" onClick={() => void logout()} title="Çıkış">
            <LogOut className="h-4 w-4" />
          </button>
        </div>

        <div className="ml-2 border-l border-surface-border pl-4">
          <BtcLogo className="h-9 w-auto" />
        </div>
      </div>
    </header>
  );
}
