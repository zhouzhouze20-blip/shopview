const MOBILE_USER_AGENT = /Android|iPhone|iPad|iPod|IEMobile|Mobile|Opera Mini/i;
const WECOM_USER_AGENT = /wxwork/i;

export interface MobileClientSignals {
  userAgent?: string;
  viewportWidth?: number;
}

export function isMobileClient(signals: MobileClientSignals = {}): boolean {
  const userAgent = signals.userAgent ?? (typeof navigator === "undefined" ? "" : navigator.userAgent);
  const viewportWidth =
    signals.viewportWidth ?? (typeof window === "undefined" ? Number.POSITIVE_INFINITY : window.innerWidth);
  return MOBILE_USER_AGENT.test(userAgent) || viewportWidth < 768;
}

export function isWeComClient(userAgent?: string): boolean {
  const value = userAgent ?? (typeof navigator === "undefined" ? "" : navigator.userAgent);
  return WECOM_USER_AGENT.test(value);
}

export function shouldUseMobileHome(pathname: string, signals: MobileClientSignals = {}): boolean {
  if (pathname === "/mobile") return true;
  return isMobileClient(signals) && (pathname === "/" || pathname === "/dashboard");
}

export function shouldUseMobileLogin(pathname: string, signals: MobileClientSignals = {}): boolean {
  return pathname === "/mobile" || pathname.startsWith("/mobile/") || isMobileClient(signals);
}
