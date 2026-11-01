import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, clearTokens, hasToken } from "./api";
import type { User } from "../types";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  refreshMe: () => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>({ user: null, loading: true, refreshMe: async () => {}, logout: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = async () => {
    if (!hasToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api.get<User>("/me"));
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  useEffect(() => {
    refreshMe();
  }, []);

  return <Ctx.Provider value={{ user, loading, refreshMe, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
