import { createContext, useContext, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api";

export interface AuthUser {
  user_id: number;
  username: string;
  real_name?: string | null;
  status: string;
  is_active: boolean;
  role_codes: string[];
  role_names: string[];
  permission_codes: string[];
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();

  const refresh = async () => {
    try {
      const data = await apiGet<AuthUser>("/api/auth/me");
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    const handleFunctionPermissionDenied = () => {
      void refresh();
    };

    window.addEventListener("shopview:function-permission-denied", handleFunctionPermissionDenied);
    return () => {
      window.removeEventListener("shopview:function-permission-denied", handleFunctionPermissionDenied);
    };
  }, []);

  const login = async (username: string, password: string) => {
    const response = await apiPost<{ message: string; user: AuthUser }>("/api/auth/login", { username, password });
    queryClient.clear();
    setUser(response.user);
    const currentUrl = `${window.location.pathname || "/"}${window.location.search}${window.location.hash}`;
    window.history.replaceState(null, "", currentUrl);
  };

  const logout = async () => {
    setUser(null);
    queryClient.clear();
    await apiPost("/api/auth/logout", {});
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
