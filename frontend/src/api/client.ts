import type {
  Analytics,
  ChatTurnResponse,
  JobRow,
  SolutionRow,
  Ticket,
  User,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

type RequestOptions = RequestInit & {
  authRetried?: boolean;
  skipAuthLogout?: boolean;
};

let unauthorizedHandler: (() => void) | null = null;
let refreshPromise: Promise<boolean> | null = null;
let currentToken: string | null = null;

export function setUnauthorizedHandler(handler: () => void) {
  unauthorizedHandler = handler;
}

export function setCurrentAuthToken(token: string | null) {
  currentToken = token;
}

function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function tryRefreshSession(token: string): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = fetch(`${API_BASE}/api/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(token),
    },
  })
    .then((response) => response.ok)
    .catch(() => false)
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
  token: string | null = null,
): Promise<T> {
  const { authRetried = false, skipAuthLogout = false, ...fetchOptions } = options;
  const activeToken = token ?? currentToken;

  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(activeToken),
      ...(fetchOptions.headers ?? {}),
    },
  });

  if (
    response.status === 401 &&
    activeToken &&
    !skipAuthLogout &&
    !authRetried &&
    !path.includes("/auth/login")
  ) {
    const refreshed = await tryRefreshSession(activeToken);
    if (refreshed) {
      return request<T>(path, { ...options, authRetried: true }, activeToken);
    }
    unauthorizedHandler?.();
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () =>
    request<{ llm_active: boolean; llm_provider: string }>("/api/health"),

  login: (email: string, password: string) =>
    request<{ token: string; user: User; expires_at?: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: (token: string) =>
    request<{ status: string }>(
      "/api/auth/logout",
      { method: "POST" },
      token,
    ),

  me: (token: string) =>
    request<User>("/api/auth/me", { skipAuthLogout: true }, token),

  refresh: (token: string) =>
    request<{ user: User; expires_at?: string }>(
      "/api/auth/refresh",
      { method: "POST", skipAuthLogout: true },
      token,
    ),

  chatTurn: (
    token: string,
    payload: {
      text: string;
      history: { role: string; content: string }[];
      phase: string;
      last_rule_id: string | null;
      last_ticket_id: string | null;
      slots: Record<string, string>;
      classification: Record<string, unknown> | null;
    },
  ) =>
    request<ChatTurnResponse>(
      "/api/chat/turn",
      { method: "POST", body: JSON.stringify(payload) },
      token,
    ),

  tickets: (token: string) =>
    request<Ticket[]>("/api/tickets", {}, token),

  resolveTicket: (token: string, ticketId: string) =>
    request<Ticket>(
      `/api/tickets/${ticketId}/status?status=resolved`,
      { method: "PATCH" },
      token,
    ),

  analytics: (token: string) =>
    request<Analytics>("/api/analytics", {}, token),

  jobs: (token: string) => request<JobRow[]>("/api/jobs", {}, token),

  runJobs: (token: string) =>
    request<{ count: number; jobs: JobRow[] }>(
      "/api/jobs/run",
      { method: "POST" },
      token,
    ),

  solutions: (token: string) =>
    request<SolutionRow[]>("/api/solutions", {}, token),

  feedback: (token: string, solutionId: string, helpful: boolean) =>
    request<{ status: string }>(
      `/api/solutions/${solutionId}/feedback`,
      {
        method: "POST",
        body: JSON.stringify({ helpful, comment: "UI geri bildirimi" }),
      },
      token,
    ),
};
