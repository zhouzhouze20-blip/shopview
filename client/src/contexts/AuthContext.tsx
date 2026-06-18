import { createContext, useContext, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api";

export interface AuthUser {
  user_id: number;
  username: string;
  real_name?: string | null;
  employee_no?: string | null;
  status: string;
  is_active: boolean;
  role_codes: string[];
  role_names: string[];
  permission_codes: string[];
}

interface AuthContextValue {
  user: AuthUser | null;
  menuUser: AuthUser | null;
  adminViewUsers: AuthUser[];
  adminViewUser: AuthUser | null;
  adminViewLoading: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  setAdminViewUserId: (userId: number | null) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const ADMIN_ROLE_CODES = new Set(["super_admin", "system_admin"]);
const ADMIN_VIEW_STORAGE_KEY = "shopview_admin_view_user_id";

function isAdminUser(user: AuthUser | null): boolean {
  return Boolean(user?.role_codes?.some((roleCode) => ADMIN_ROLE_CODES.has(roleCode)));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [adminViewUsers, setAdminViewUsers] = useState<AuthUser[]>([]);
  const [adminViewUserId, setAdminViewUserIdState] = useState<number | null>(() => {
    const saved = window.localStorage.getItem(ADMIN_VIEW_STORAGE_KEY);
    const parsed = saved ? Number(saved) : NaN;
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  });
  const [adminViewLoading, setAdminViewLoading] = useState(false);
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
    if (!isAdminUser(user)) {
      setAdminViewUsers([]);
      setAdminViewUserIdState(null);
      setAdminViewLoading(false);
      window.localStorage.removeItem(ADMIN_VIEW_STORAGE_KEY);
      return;
    }

    let canceled = false;
    setAdminViewLoading(true);
    apiGet<AuthUser[]>("/api/auth/admin-view/users")
      .then((users) => {
        if (canceled) return;
        setAdminViewUsers(users);
      })
      .catch(() => {
        if (canceled) return;
        setAdminViewUsers([]);
        setAdminViewUserIdState(null);
        window.localStorage.removeItem(ADMIN_VIEW_STORAGE_KEY);
      })
      .finally(() => {
        if (!canceled) setAdminViewLoading(false);
      });

    return () => {
      canceled = true;
    };
  }, [user?.user_id, user?.role_codes?.join("|")]);

  useEffect(() => {
    if (!adminViewUserId) return;
    if (!adminViewUsers.length) return;
    if (!adminViewUsers.some((candidate) => candidate.user_id === adminViewUserId)) {
      setAdminViewUserIdState(null);
      window.localStorage.removeItem(ADMIN_VIEW_STORAGE_KEY);
    }
  }, [adminViewUserId, adminViewUsers]);

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
    setAdminViewUsers([]);
    setAdminViewUserIdState(null);
    window.localStorage.removeItem(ADMIN_VIEW_STORAGE_KEY);
    setUser(response.user);
    const currentUrl = `${window.location.pathname || "/"}${window.location.search}${window.location.hash}`;
    window.history.replaceState(null, "", currentUrl);
  };

  const logout = async () => {
    setUser(null);
    setAdminViewUsers([]);
    setAdminViewUserIdState(null);
    window.localStorage.removeItem(ADMIN_VIEW_STORAGE_KEY);
    queryClient.clear();
    await apiPost("/api/auth/logout", {});
  };

  const setAdminViewUserId = (userId: number | null) => {
    if (!isAdminUser(user) || userId === user?.user_id) {
      setAdminViewUserIdState(null);
      window.localStorage.removeItem(ADMIN_VIEW_STORAGE_KEY);
      queryClient.clear();
      return;
    }
    setAdminViewUserIdState(userId);
    window.localStorage.setItem(ADMIN_VIEW_STORAGE_KEY, String(userId));
    queryClient.clear();
  };

  const adminViewUser =
    adminViewUserId && isAdminUser(user)
      ? adminViewUsers.find((candidate) => candidate.user_id === adminViewUserId) ?? null
      : null;
  const menuUser = adminViewUser ?? user;

  return (
    <AuthContext.Provider
      value={{
        user,
        menuUser,
        adminViewUsers,
        adminViewUser,
        adminViewLoading,
        loading,
        login,
        logout,
        refresh,
        setAdminViewUserId,
      }}
    >
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
