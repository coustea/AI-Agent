import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  api,
  getAuthToken,
  setAuthToken,
  setUnauthorizedHandler,
} from "@/lib/api";
import type { User } from "@/types/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => Boolean(getAuthToken()));

  const logout = useCallback(() => {
    setAuthToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setLoading(false);
      return;
    }
    const ctrl = new AbortController();
    api
      .profile(ctrl.signal)
      .then((u) => {
        if (!ctrl.signal.aborted) setUser(u);
      })
      .catch((err) => {
        if ((err as Error).name === "AbortError" || ctrl.signal.aborted) return;
        setAuthToken(null);
        setUser(null);
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setLoading(false);
      });
    return () => {
      ctrl.abort();
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const resp = await api.login({ email, password });
    setAuthToken(resp.token);
    setUser(resp.user);
  }, []);

  const register = useCallback(async (username: string, email: string, password: string) => {
    const resp = await api.register({ username, email, password });
    setAuthToken(resp.token);
    setUser(resp.user);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
