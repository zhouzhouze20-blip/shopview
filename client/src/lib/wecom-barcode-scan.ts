import { apiGet } from "@/lib/api";

type WeComJsSdkConfig = {
  appId: string;
  timestamp: number;
  nonceStr: string;
  signature: string;
  jsApiList: string[];
};

type WeComScanResult = {
  resultStr?: string;
  errMsg?: string;
};

type WeComSdk = {
  config: (config: WeComJsSdkConfig & { debug: boolean }) => void;
  ready: (callback: () => void) => void;
  error: (callback: (error: unknown) => void) => void;
  scanQRCode: (options: {
    needResult: number;
    scanType: string[];
    success: (result: WeComScanResult) => void;
    cancel?: () => void;
    fail?: (error: unknown) => void;
  }) => void;
};

declare global {
  interface Window {
    wx?: WeComSdk;
  }
}

const WECOM_JS_SDK_URL = "https://res.wx.qq.com/open/js/jweixin-1.6.0.js";
let sdkPromise: Promise<WeComSdk> | null = null;

export class ScanCancelledError extends Error {
  constructor() {
    super("用户取消扫码");
    this.name = "ScanCancelledError";
  }
}

export const normalizeScannedBarcode = (value: string) => {
  const trimmed = String(value || "").trim();
  const separatorIndex = trimmed.indexOf(",");
  if (separatorIndex <= 0) return trimmed;

  const prefix = trimmed.slice(0, separatorIndex).trim();
  const payload = trimmed.slice(separatorIndex + 1).trim();
  return /^[A-Z0-9_]+$/i.test(prefix) && payload ? payload : trimmed;
};

const isWeComClient = () => /wxwork/i.test(window.navigator.userAgent || "");

const loadWeComSdk = () => {
  if (window.wx) return Promise.resolve(window.wx);
  if (sdkPromise) return sdkPromise;

  sdkPromise = new Promise<WeComSdk>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${WECOM_JS_SDK_URL}"]`);
    const script = existing ?? document.createElement("script");
    const onLoad = () => window.wx ? resolve(window.wx) : reject(new Error("企业微信扫码组件加载失败"));
    script.addEventListener("load", onLoad, { once: true });
    script.addEventListener("error", () => reject(new Error("企业微信扫码组件加载失败")), { once: true });
    if (!existing) {
      script.src = WECOM_JS_SDK_URL;
      script.async = true;
      document.head.appendChild(script);
    }
  });
  return sdkPromise;
};

export const tryWeComBarcodeScan = async (): Promise<string | null> => {
  if (!isWeComClient()) return null;

  const signedUrl = window.location.href.split("#", 1)[0];
  const [sdk, config] = await Promise.all([
    loadWeComSdk(),
    apiGet<WeComJsSdkConfig>(`/api/auth/wecom/js-sdk-config?url=${encodeURIComponent(signedUrl)}`),
  ]);

  return new Promise<string>((resolve, reject) => {
    let settled = false;
    const timeout = window.setTimeout(() => {
      if (!settled) {
        settled = true;
        reject(new Error("企业微信扫码初始化超时"));
      }
    }, 8000);
    const finish = (callback: () => void) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeout);
      callback();
    };

    sdk.error((error) => finish(() => reject(new Error(`企业微信扫码初始化失败：${String(error)}`))));
    sdk.ready(() => {
      sdk.scanQRCode({
        needResult: 1,
        scanType: ["barCode"],
        success: (result) => finish(() => {
          const barcode = normalizeScannedBarcode(result.resultStr || "");
          if (barcode) resolve(barcode);
          else reject(new Error("没有识别到商品条码"));
        }),
        cancel: () => finish(() => reject(new ScanCancelledError())),
        fail: (error) => finish(() => reject(new Error(`企业微信扫码失败：${String(error)}`))),
      });
    });
    sdk.config({ debug: false, ...config });
  });
};
