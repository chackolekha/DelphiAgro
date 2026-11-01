import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, clearTokens } from "./api";
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
    // Always ask the backend: in DEV_NO_AUTH mode /me returns the demo user
    // even without a token; in prod a tokenless call 401s and user stays null.
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
