import { AnalyticsPage } from "./components/AnalyticsPage";
import { ChatPanel } from "./components/ChatPanel";
import { KnowledgeBasePage } from "./components/KnowledgeBasePage";
import { LoginPage } from "./components/LoginPage";
import { Sidebar, type PageId } from "./components/layout/Sidebar";
import { TopBar } from "./components/layout/TopBar";
import { TicketsPage } from "./components/TicketsPage";
import { useAuth } from "./context/AuthContext";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";

export default function App() {
  const { token, bootstrapping } = useAuth();
  const [page, setPage] = useState<PageId>("chat");

  if (bootstrapping) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-muted">
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <LoaderCircle className="h-5 w-5 animate-spin text-brand-600" />
          Oturum doğrulanıyor...
        </div>
      </div>
    );
  }

  if (!token) {
    return <LoginPage />;
  }

  return (
    <div className="flex min-h-screen bg-surface-muted">
      <Sidebar active={page} onNavigate={setPage} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar page={page} />
        <main className="relative flex-1">
          {/* ChatPanel unmount edilmez — sayfa geçişlerinde mesajlar korunur */}
          <div className={page === "chat" ? "h-full" : "hidden"}>
            <ChatPanel />
          </div>
          {page === "tickets" && <TicketsPage />}
          {page === "analytics" && <AnalyticsPage />}
          {page === "kb" && <KnowledgeBasePage />}
        </main>
      </div>
    </div>
  );
}
