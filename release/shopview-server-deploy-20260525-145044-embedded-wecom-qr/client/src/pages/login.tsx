import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, LockKeyhole, QrCode, ShieldCheck, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet } from "@/lib/api";

const wecomErrorMessages: Record<string, string> = {
  wecom_api_failed: "企业微信登录接口调用失败，请稍后重试或联系管理员。",
  wecom_disabled: "账号已停用，无法通过企业微信登录。",
  wecom_missing_code: "企业微信登录缺少授权码，请重新扫码。",
  wecom_no_userid: "企业微信未返回成员身份，请确认使用企业微信 App 扫码。",
  wecom_state_invalid: "企业微信登录状态已失效，请重新扫码。",
  wecom_unbound: "企业微信账号未开通 ShopView，请联系管理员绑定账号。",
};

const businessUnits = ["常州购物中心", "常州百货大楼", "常州新世纪", "常州半山书局"];

export default function LoginPage() {
  const { login } = useAuth();
  const [activeTab, setActiveTab] = useState("password");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [wecomSubmitting, setWecomSubmitting] = useState(false);
  const [wecomLoginUrl, setWecomLoginUrl] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const authError = params.get("auth_error");
    if (!authError) return;

    const detail = params.get("wecom_detail");
    const message = wecomErrorMessages[authError] || "企业微信登录失败，请重新扫码。";
    setError(detail ? `${message}（${detail}）` : message);
    params.delete("auth_error");
    params.delete("wecom_detail");
    const nextSearch = params.toString();
    const nextUrl = `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ""}${window.location.hash}`;
    window.history.replaceState(null, "", nextUrl);
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  };

  const loadWecomLoginUrl = useCallback(async () => {
    setWecomSubmitting(true);
    setError("");
    try {
      const currentPath = `${window.location.pathname || "/"}${window.location.search}${window.location.hash}`;
      const response = await apiGet<{ login_url: string }>(
        `/api/auth/wecom/login-url?next=${encodeURIComponent(currentPath)}`,
      );
      setWecomLoginUrl(response.login_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "企业微信扫码登录暂不可用");
    } finally {
      setWecomSubmitting(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab !== "wecom" || wecomLoginUrl || wecomSubmitting) return;
    void loadWecomLoginUrl();
  }, [activeTab, loadWecomLoginUrl, wecomLoginUrl, wecomSubmitting]);

  useEffect(() => {
    if (activeTab !== "wecom" || !wecomLoginUrl) return;
    const timer = window.setInterval(async () => {
      try {
        await apiGet("/api/auth/me");
        window.location.replace("/");
      } catch {
        // Continue polling while the QR code is waiting for confirmation.
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [activeTab, wecomLoginUrl]);

  const handleWecomLogin = () => {
    setWecomLoginUrl("");
    void loadWecomLoginUrl();
  };

  return (
    <main
      className="relative min-h-screen overflow-hidden bg-slate-950 bg-cover bg-center"
      style={{
        backgroundImage:
          'linear-gradient(90deg, rgba(5, 14, 27, 0.74) 0%, rgba(5, 14, 27, 0.42) 44%, rgba(5, 14, 27, 0.2) 100%), url("/assets/login-bg-changzhou-commerce.png")',
      }}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(94,202,188,0.24),transparent_28%),linear-gradient(180deg,rgba(6,12,22,0.12),rgba(6,12,22,0.4))]" />

      <section className="relative z-10 mx-auto grid min-h-screen w-full max-w-6xl grid-cols-1 items-center gap-8 px-5 py-10 lg:grid-cols-[minmax(0,1fr)_430px] lg:gap-16 lg:px-8">
        <div className="max-w-xl text-white">
          <div className="inline-flex h-10 items-center gap-3 rounded-full border border-white/30 bg-white/10 px-4 text-sm text-white/90 backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-teal-300 shadow-[0_0_20px_rgba(94,234,212,0.9)]" />
            ShopView 统一经营管理平台
          </div>

          <h1 className="mt-7 text-4xl font-bold leading-tight tracking-normal text-white sm:text-5xl lg:text-[46px] xl:text-[54px]">
            一站式掌握
            <br />
            商业经营现场
          </h1>
          <p className="mt-5 max-w-lg text-base leading-8 text-slate-100/80 sm:text-lg">
            汇聚购物中心、百货、商业综合体与书店文化空间的经营数据，为门店、柜位、合同与销售分析提供统一入口。
          </p>

          <div className="mt-8 grid max-w-lg grid-cols-1 gap-3 text-sm text-white/85 sm:grid-cols-2">
            {businessUnits.map((unit) => (
              <div
                key={unit}
                className="flex min-h-14 items-center rounded-lg border border-white/20 bg-slate-950/30 px-4 backdrop-blur-md"
              >
                {unit}
              </div>
            ))}
          </div>
        </div>

        <div className="w-full rounded-lg border border-white/70 bg-white/90 p-6 shadow-[0_28px_80px_rgba(0,14,28,0.28)] backdrop-blur-2xl sm:p-7">
          <div>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold tracking-normal text-slate-900">欢迎登录</h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  请选择登录方式，进入 ShopView 经营管理工作台。
                </p>
              </div>
              <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-teal-50 text-teal-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6">
              <TabsList className="grid h-12 w-full grid-cols-2 rounded-lg border border-slate-200 bg-slate-100 p-1">
                <TabsTrigger
                  value="password"
                  className="h-10 rounded-md text-sm font-semibold data-[state=active]:bg-white data-[state=active]:text-teal-700 data-[state=active]:shadow-sm"
                >
                  用户密码登录
                </TabsTrigger>
                <TabsTrigger
                  value="wecom"
                  className="h-10 rounded-md text-sm font-semibold data-[state=active]:bg-white data-[state=active]:text-teal-700 data-[state=active]:shadow-sm"
                >
                  企业微信扫码登录
                </TabsTrigger>
              </TabsList>

              <TabsContent value="password" className="mt-6">
                <form className="space-y-5" onSubmit={handleSubmit}>
                  <div className="space-y-2">
                    <Label htmlFor="username" className="text-slate-700">
                      用户名
                    </Label>
                    <div className="relative">
                      <UserRound className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <Input
                        id="username"
                        className="h-11 rounded-lg border-slate-200 bg-white pl-10"
                        placeholder="请输入用户名"
                        value={username}
                        onChange={(event) => setUsername(event.target.value)}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-slate-700">
                      密码
                    </Label>
                    <div className="relative">
                      <LockKeyhole className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <Input
                        id="password"
                        type="password"
                        className="h-11 rounded-lg border-slate-200 bg-white pl-10"
                        placeholder="请输入密码"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-sm text-slate-500">
                    <span className="inline-flex items-center gap-2">
                      <span className="h-4 w-4 rounded border border-slate-300 bg-white" />
                      记住账号
                    </span>
                    <span className="font-medium text-teal-700">忘记密码？</span>
                  </div>

                  {error ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                      {error}
                    </div>
                  ) : null}

                  <Button
                    type="submit"
                    className="h-11 w-full rounded-lg bg-teal-700 text-base font-semibold shadow-[0_14px_28px_rgba(15,118,110,0.24)] hover:bg-teal-800"
                    disabled={submitting}
                  >
                    {submitting ? "登录中..." : "登录"}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="wecom" className="mt-6">
                <div className="overflow-hidden rounded-lg border border-dashed border-teal-200 bg-teal-50/70">
                  {wecomLoginUrl ? (
                    <iframe
                      title="企业微信扫码登录"
                      src={wecomLoginUrl}
                      className="h-[320px] w-full border-0 bg-white"
                    />
                  ) : (
                    <div className="grid min-h-[320px] place-items-center px-4 text-center">
                      <div>
                        <QrCode className="mx-auto h-10 w-10 text-teal-700" />
                        <p className="mt-4 text-sm font-medium text-slate-700">
                          {wecomSubmitting ? "正在获取企业微信二维码..." : "切换到此页签后会自动加载二维码"}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {error ? (
                  <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {error}
                  </div>
                ) : null}

                <Button
                  type="button"
                  variant="outline"
                  className="mt-5 h-11 w-full rounded-lg border-teal-200 bg-white text-base font-semibold text-teal-700 hover:bg-teal-50 hover:text-teal-800"
                  disabled={wecomSubmitting}
                  onClick={handleWecomLogin}
                >
                  <QrCode className="mr-2 h-4 w-4" />
                  {wecomSubmitting ? "正在刷新二维码..." : "刷新企业微信二维码"}
                </Button>

                <div className="mt-4 flex items-start gap-2 rounded-lg bg-slate-50 px-3 py-3 text-xs leading-5 text-slate-500">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" />
                  若二维码已过期，请重新点击按钮获取最新授权入口。
                </div>
              </TabsContent>
            </Tabs>

            <div className="mt-6 text-center text-xs text-slate-400">© Changzhou Commercial Group</div>
          </div>
        </div>
      </section>
    </main>
  );
}
