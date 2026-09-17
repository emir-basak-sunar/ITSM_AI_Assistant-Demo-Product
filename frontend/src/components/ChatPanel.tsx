import { Bot, LoaderCircle, RotateCcw, Send, User } from "lucide-react";
import { FormEvent, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { ChatMessage, ChatSession } from "../types";
import { SimilarResolvedTicketCard } from "./SimilarResolvedTicketCard";
import { Badge, priorityVariant } from "./ui/Badge";

const WELCOME =
  "Merhaba! ITSM destek asistanıyım. Talebinizi doğal dilde yazabilirsiniz — sınıflandırır, çözüm önerir, gerekli bilgileri toplar ve bilet oluştururum.";

const QUICK_ACTIONS = [
  { label: "Donanım arızası", text: "Laptopum açılmıyor, ekran siyah." },
  { label: "VPN talebi", text: "VPN bağlanamıyorum, talep aç" },
  { label: "Şifre sıfırlama", text: "Şifremi unuttum hesabım kilitlendi." },
  { label: "Rapor isteği", text: "Açık taleplerin raporunu hazırla, günlük özet istiyorum." },
];

const INITIAL_SESSION: ChatSession = {
  phase: "open",
  lastRuleId: null,
  lastTicketId: null,
  slots: {},
  classification: null,
};

export function ChatPanel() {
  const { token } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: WELCOME },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [session, setSession] = useState<ChatSession>(INITIAL_SESSION);
  const bottomRef = useRef<HTMLDivElement>(null);

  const history = useMemo(
    () => messages.map((m) => ({ role: m.role, content: m.content })),
    [messages],
  );

  async function sendText(text: string) {
    if (!token || !text.trim() || loading) return;
    const userText = text.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setLoading(true);
    try {
      const result = await api.chatTurn(token, {
        text: userText,
        history,
        phase: session.phase,
        last_rule_id: session.lastRuleId,
        last_ticket_id: session.lastTicketId,
        slots: session.slots,
        classification: session.classification as Record<string, unknown> | null,
      });
      const meta = result.classification?.path_label ?? undefined;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.reply,
          meta,
          priority: result.classification?.priority,
          similarTickets: result.similar_tickets?.length ? result.similar_tickets : undefined,
        },
      ]);
      setSession({
        phase: result.phase,
        lastRuleId: result.last_rule_id,
        lastTicketId: result.ticket?.id
          ? String(result.ticket.id)
          : result.debug.action === "resolved"
            ? null
            : session.lastTicketId,
        slots: result.slots ?? {},
        classification: result.classification,
      });
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Bir hata oluştu: ${err instanceof Error ? err.message : "bilinmeyen hata"}`,
        },
      ]);
    } finally {
      setLoading(false);
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }

  function resetChat() {
    setMessages([{ role: "assistant", content: WELCOME }]);
    setSession(INITIAL_SESSION);
    setInput("");
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-surface-border bg-white px-6 py-3">
        <p className="text-sm text-slate-500">
          Yapay zeka destekli L1 destek hattı
        </p>
        <button type="button" className="btn-secondary" onClick={resetChat}>
          <RotateCcw className="h-4 w-4" />
          Yeni sohbet
        </button>
      </div>

      {/* Mesajlar */}
      <div className="flex-1 overflow-y-auto bg-surface-muted px-6 py-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.map((message, index) => {
            const isUser = message.role === "user";
            return (
              <div key={`${message.role}-${index}`} className="flex flex-row gap-3">
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                    isUser ? "bg-slate-700 text-white" : "bg-white text-brand-600 shadow-card ring-1 ring-surface-border"
                  }`}
                >
                  {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>
                <div className="max-w-[75%] text-left">
                  <p className="mb-1 text-xs font-medium text-slate-400">
                    {isUser ? "Siz" : "Asistan"}
                  </p>
                  <div
                    className={`inline-block rounded-2xl rounded-tl-md px-4 py-3 text-sm leading-relaxed ${
                      isUser
                        ? "bg-slate-100 text-slate-800 ring-1 ring-surface-border"
                        : "bg-white text-slate-700 shadow-card ring-1 ring-surface-border"
                    }`}
                  >
                    <div className="markdown-body">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  </div>
                  {message.meta ? (
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className="text-xs text-slate-400">{message.meta}</span>
                      {"priority" in message && message.priority ? (
                        <Badge variant={priorityVariant(String(message.priority))}>
                          {String(message.priority)}
                        </Badge>
                      ) : null}
                    </div>
                  ) : null}

                  {!isUser && message.similarTickets?.length ? (
                    <div className="mt-4 space-y-3">
                      {message.similarTickets.map((ticket) => (
                        <SimilarResolvedTicketCard key={ticket.id ?? ticket.customer_ask} ticket={ticket} />
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}

          {loading ? (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <LoaderCircle className="h-4 w-4 animate-spin text-brand-600" />
              Yanıt hazırlanıyor...
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Giriş alanı */}
      <div className="border-t border-surface-border bg-white px-6 py-4">
        <div className="mx-auto max-w-3xl">
          <form
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              void sendText(input);
            }}
            className="flex gap-3"
          >
            <input
              className="input-field flex-1"
              placeholder="Talebinizi yazın..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button type="submit" className="btn-primary" disabled={loading || !input.trim()}>
              <Send className="h-4 w-4" />
              Gönder
            </button>
          </form>
          <div className="mt-3 flex flex-wrap gap-2">
            {QUICK_ACTIONS.map(({ label, text }) => (
              <button
                key={label}
                type="button"
                className="rounded-full border border-surface-border bg-white px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                onClick={() => void sendText(text)}
                disabled={loading}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
