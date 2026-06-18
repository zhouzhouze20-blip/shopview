const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");
const APP_ASSET_PREFIXES = ["/uploads/", "/static/", "/assets/"];
const DEFAULT_API_PORT = import.meta.env.VITE_API_PORT?.trim() || "8000";
const ADMIN_VIEW_STORAGE_KEY = "shopview_admin_view_user_id";
const getBackendOrigin = () => {
  const { hostname, protocol } = window.location;
  return `${protocol}//${hostname}:${DEFAULT_API_PORT}`;
};

const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL?.trim();
  if (envUrl) {
    return trimTrailingSlash(envUrl);
  }

  if (import.meta.env.DEV) {
    return "";
  }

  const { hostname, protocol, port } = window.location;
  if ((hostname === "localhost" || hostname === "127.0.0.1") && port !== DEFAULT_API_PORT) {
    return `${protocol}//${hostname}:${DEFAULT_API_PORT}`;
  }

  return "";
};

export const getApiUrl = () => getApiBaseUrl();

const getAssetBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL?.trim();
  if (envUrl) {
    return trimTrailingSlash(envUrl);
  }

  if (import.meta.env.DEV) {
    return getBackendOrigin();
  }

  return getApiBaseUrl();
};

export const API_BASE_URL = getApiUrl();

export const resolveApiAssetUrl = (fileUrl?: string | null) => {
  if (!fileUrl) return "";
  if (fileUrl.startsWith("data:")) return fileUrl;

  const assetBaseUrl = getAssetBaseUrl();

  if (!/^(https?:)?\/\//i.test(fileUrl)) {
    if (!assetBaseUrl) return fileUrl;
    return `${assetBaseUrl}${fileUrl.startsWith("/") ? fileUrl : `/${fileUrl}`}`;
  }

  try {
    const url = new URL(fileUrl, window.location.origin);
    const isAppAsset = APP_ASSET_PREFIXES.some((prefix) => url.pathname.startsWith(prefix));
    if (!isAppAsset) return fileUrl;

    if (!assetBaseUrl) {
      return fileUrl;
    }

    return `${assetBaseUrl}${url.pathname}${url.search}${url.hash}`;
  } catch {
    return fileUrl;
  }
};

export const apiRequest = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> => {
  // 每次请求时动态获取API地址
  const apiBaseUrl = getApiUrl();
  const url = `${apiBaseUrl}${endpoint}`;
  
  const defaultOptions: RequestInit = {
    credentials: "include",
    headers: {
      'Content-Type': 'application/json',
      ...(window.localStorage.getItem(ADMIN_VIEW_STORAGE_KEY)
        ? { "X-ShopView-Admin-View-User-Id": window.localStorage.getItem(ADMIN_VIEW_STORAGE_KEY)! }
        : {}),
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, defaultOptions);
  
  if (!response.ok) {
    const errorText = await response.text();
    if (response.status === 403 && errorText.includes("无功能权限")) {
      window.dispatchEvent(
        new CustomEvent("shopview:function-permission-denied", {
          detail: { endpoint, status: response.status, body: errorText },
        }),
      );
    }
    throw new Error(`API请求失败: ${response.status} - ${errorText}`);
  }
  
  return response;
};

export const apiGet = <T>(endpoint: string): Promise<T> => 
  apiRequest(endpoint).then(res => res.json());

export const apiPost = <T>(endpoint: string, data?: any): Promise<T> => 
  apiRequest(endpoint, {
    method: 'POST',
    body: JSON.stringify(data),
  }).then(res => res.json());

export const apiPut = <T>(endpoint: string, data?: any): Promise<T> => 
  apiRequest(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
  }).then(res => res.json());

export const apiDelete = <T>(endpoint: string): Promise<T> => 
  apiRequest(endpoint, {
    method: 'DELETE',
  }).then(res => res.json());
