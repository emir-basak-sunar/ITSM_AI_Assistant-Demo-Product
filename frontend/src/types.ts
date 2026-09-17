export interface User {
  email: string;
  name: string;
  role: string;
}

export interface TicketMessage {
  role: "user" | "agent";
  content: string;
  at?: string;
}

export interface SimilarResolvedTicket {
  id?: string;
  score?: number;
  similarity_pct?: number;
  status?: string;
  path_label?: string;
  surec_label?: string;
  birim_label?: string;
  priority?: string;
  customer_ask?: string;
  resolution_summary?: string;
  created_at?: string;
  resolved_at?: string;
  messages?: TicketMessage[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  meta?: string;
  priority?: string;
  similarTickets?: SimilarResolvedTicket[];
}

export interface Classification {
  path_label?: string;
  priority?: string;
  birim_label?: string;
  surec_label?: string;
  unclear?: boolean;
}

export interface ChatTurnResponse {
  reply: string;
  phase: string;
  last_rule_id: string | null;
  ticket: Record<string, unknown> | null;
  debug: Record<string, unknown>;
  slots: Record<string, string>;
  classification: Classification | null;
  similar_tickets?: SimilarResolvedTicket[];
}

export interface Ticket {
  id: string;
  status: string;
  urgency: string;
  priority?: string;
  path_label?: string;
  customer_ask?: string;
  birim_label?: string;
  created_at?: string;
  slots?: Record<string, string>;
}

export interface Analytics {
  total_tickets: number;
  resolved: number;
  open: number;
  feedback: {
    overall_success_rate: number;
    total_feedback: number;
  };
}

export interface SolutionRow {
  id: string;
  title: string;
  surec_label: string;
  birim_label: string;
  modul_label: string;
  talep_turu: string;
  steps: string[];
  zorunlu_alanlar: string[];
  self_service_uygun_mu?: boolean;
  module_overview?: string;
  common_transactions?: string[];
  common_issues?: string[];
  stats: {
    rating_display: string;
    success_rate: number;
  };
}

export interface JobRow {
  id: string;
  command: string;
  status: string;
  created_at: string;
  result?: string;
}

export interface ChatSession {
  phase: string;
  lastRuleId: string | null;
  lastTicketId: string | null;
  slots: Record<string, string>;
  classification: Classification | null;
}
