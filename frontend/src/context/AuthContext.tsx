import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, setCurrentAuthToken, setUnauthorizedHandler } from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  token: string | null;
  user: User | null;
  bootstrapping: boolean;
  llmActive: boolean;
  llmProvider: string;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = "itsm_token";
const USER_KEY = "itsm_user";
const KEEPALIVE_MS = 5 * 60 * 1000;

function clearStoredAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [bootstrapping, setBootstrapping] = useState(
    () => Boolean(localStorage.getItem(TOKEN_KEY)),
  );
  const [llmActive, setLlmActive] = useState(false);
  const [llmProvider, setLlmProvider] = useState("Hibrit RAG");

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearStoredAuth();
      setCurrentAuthToken(null);
      setToken(null);
      setUser(null);
    });
  }, []);

  useEffect(() => {
    setCurrentAuthToken(token);
  }, [token]);

  useEffect(() => {
    api
      .health()
      .then((res) => {
        setLlmActive(res.llm_active);
        setLlmProvider(res.llm_provider || "Hibrit RAG");
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (!storedToken) {
      setBootstrapping(false);
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const refreshed = await api.refresh(storedToken);
        if (cancelled) return;
        setToken(storedToken);
        setUser(refreshed.user);
        localStorage.setItem(USER_KEY, JSON.stringify(refreshed.user));
      } catch {
        try {
          const me = await api.me(storedToken);
          if (cancelled) return;
          setToken(storedToken);
          setUser(me);
          localStorage.setItem(USER_KEY, JSON.stringify(me));
        } catch {
          if (cancelled) return;
          clearStoredAuth();
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setBootstrapping(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!token) return;

    const refreshSession = () => {
      void api.refresh(token).then((res) => {
        setUser(res.user);
        localStorage.setItem(USER_KEY, JSON.stringify(res.user));
      }).catch(() => undefined);
    };

    refreshSession();
    const intervalId = window.setInterval(refreshSession, KEEPALIVE_MS);
    const onFocus = () => refreshSession();
    window.addEventListener("focus", onFocus);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", onFocus);
    };
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      bootstrapping,
      llmActive,
      llmProvider,
      login: async (email, password) => {
        const res = await api.login(email, password);
        localStorage.setItem(TOKEN_KEY, res.token);
        localStorage.setItem(USER_KEY, JSON.stringify(res.user));
        setCurrentAuthToken(res.token);
        setToken(res.token);
        setUser(res.user);
      },
      logout: async () => {
        if (token) {
          try {
            await api.logout(token);
          } catch {
            /* ignore */
          }
        }
        clearStoredAuth();
        setCurrentAuthToken(null);
        setToken(null);
        setUser(null);
      },
    }),
    [token, user, bootstrapping, llmActive, llmProvider],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
