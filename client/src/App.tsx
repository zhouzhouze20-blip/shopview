import { Router, Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import AuthLoadingScreen from "@/components/auth-loading-screen";
import { StoreProvider } from "@/contexts/StoreContext";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import MainDashboard from "@/pages/main-dashboard";
import StoresPage from "@/pages/stores";
import CountersPage from "@/pages/counters";
import LoginPage from "@/pages/login";
import MobileHomePage from "@/pages/mobile-home";
import MobileSalesDashboardPage from "@/pages/mobile-sales-dashboard";
import MobileContractsPage from "@/pages/mobile-contracts";
import MobileInventoryPage from "@/pages/mobile-inventory";
import MobileRevenueDashboardPage from "@/pages/mobile-revenue-dashboard";
import MobileRentalReceivablesPage from "@/pages/mobile-rental-receivables";
import MobileCouponFollowupsPage from "@/pages/mobile-coupon-followups";
import MobileSupplierPaymentsPage from "@/pages/mobile-supplier-payments";
import { shouldUseMobileHome } from "@/lib/mobile-entry";
// Floor definition/management pages removed
import NotFound from "@/pages/not-found";

// 生产环境使用 Vite base (/static/)，开发环境使用根路径
const BASE = import.meta.env.DEV
  ? ""
  : (import.meta.env.BASE_URL || "/").replace(/\/$/, "");

function Routes() {
  const ResponsiveDashboard = () =>
    shouldUseMobileHome(window.location.pathname) ? <MobileHomePage /> : <MainDashboard />;

  return (
    <Switch>
      <Route path="/mobile/sales" component={MobileSalesDashboardPage} />
      <Route path="/mobile/contracts" component={MobileContractsPage} />
      <Route path="/mobile/inventory" component={MobileInventoryPage} />
      <Route path="/mobile/revenue" component={MobileRevenueDashboardPage} />
      <Route path="/mobile/rental-receivables" component={MobileRentalReceivablesPage} />
      <Route path="/mobile/coupon-followups" component={MobileCouponFollowupsPage} />
      <Route path="/mobile/supplier-payments" component={MobileSupplierPaymentsPage} />
      <Route path="/mobile" component={MobileHomePage} />
      <Route path="/" component={ResponsiveDashboard} />
      <Route path="/stores" component={StoresPage} />
      <Route path="/counters" component={CountersPage} />
      <Route path="/dashboard" component={ResponsiveDashboard} />
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
    return <AuthLoadingScreen />;
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
