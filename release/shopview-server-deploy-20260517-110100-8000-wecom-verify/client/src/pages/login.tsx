import { useEffect, useState } from "react";
import { Building2, CheckCircle2, LockKeyhole, QrCode, ShieldCheck, UserRound } from "lucide-react";
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

const qrCells = Array.from({ length: 49 }, (_, index) => {
  const row = Math.floor(index / 7);
  const col = index % 7;
  const finder =
    (row <= 1 && col <= 1) ||
    (row <= 1 && col >= 5) ||
    (row >= 5 && col <= 1);
  const filled = finder || (row * 3 + col * 5) % 4 !== 1;
  return { filled, tone: finder ? "dark" : (row + col) % 3 === 0 ? "teal" : "muted" };
});

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [wecomSubmitting, setWecomSubmitting] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const authError = params.get("auth_error");
    if (!authError) return;

    setError(wecomErrorMessages[authError] || "企业微信登录失败，请重新扫码。");
    params.delete("auth_error");
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

  const handleWecomLogin = async () => {
    setWecomSubmitting(true);
    setError("");
    try {
      const currentPath = `${window.location.pathname || "/"}${window.location.search}${window.location.hash}`;
      const response = await apiGet<{ login_url: string }>(
        `/api/auth/wecom/login-url?next=${encodeURIComponent(currentPath)}`,
      );
      window.location.href = response.login_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "企业微信扫码登录暂不可用");
      setWecomSubmitting(false);
    }
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

          <h1 className="mt-7 text-4xl font-bold leading-tight tracking-normal text-white sm:text-5xl lg:text-[54px]">
            一站式掌握商业经营现场
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

            <Tabs defaultValue="password" className="mt-6">
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
                <div className="rounded-lg border border-dashed border-teal-200 bg-teal-50/70 p-4">
                  <div className="grid grid-cols-[124px_minmax(0,1fr)] items-center gap-4">
                    <div className="grid h-[124px] w-[124px] grid-cols-7 grid-rows-7 gap-1 rounded-lg border border-slate-200 bg-white p-2">
                      {qrCells.map((cell, index) => (
                        <span
                          key={index}
                          className={
                            cell.filled
                              ? cell.tone === "dark"
                                ? "rounded-sm bg-slate-900"
                                : cell.tone === "teal"
                                  ? "rounded-sm bg-teal-700"
                                  : "rounded-sm bg-teal-700/35"
                              : "rounded-sm bg-transparent"
                          }
                        />
                      ))}
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">企业微信扫码登录</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-500">
                        使用企业微信 App 扫描授权二维码，系统将自动识别已绑定的员工账号。
                      </p>
                    </div>
                  </div>
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
                  {wecomSubmitting ? "正在打开企业微信..." : "打开企业微信扫码"}
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
