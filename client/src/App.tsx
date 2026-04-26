import { Router, Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { StoreProvider } from "@/contexts/StoreContext";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import MainDashboard from "@/pages/main-dashboard";
import StoresPage from "@/pages/stores";
import CountersPage from "@/pages/counters";
import CounterGroupsMapPage from "@/pages/counter-groups-map";
import LoginPage from "@/pages/login";
// Floor definition/management pages removed
import NotFound from "@/pages/not-found";

// 生产环境使用 Vite base (/static/)，开发环境使用根路径
const BASE = import.meta.env.DEV
  ? ""
  : (import.meta.env.BASE_URL || "/").replace(/\/$/, "");

function Routes() {
  return (
    <Switch>
      <Route path="/" component={StoresPage} />
      <Route path="/stores" component={StoresPage} />
      <Route path="/counters" component={CountersPage} />
      <Route path="/counter-groups-map" component={CounterGroupsMapPage} />
      <Route path="/dashboard" component={MainDashboard} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <StoreProvider>
          <TooltipProvider>
            <Toaster />
            <AppShell />
          </TooltipProvider>
        </StoreProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;

function AppShell() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-600">
        正在加载登录状态...
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <Router base={BASE}>
      <Routes />
    </Router>
  );
}
