import { useState } from "react";
import { Building2, LockKeyhole, UserRound } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

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

  return (
    <div className="min-h-screen bg-[linear-gradient(135deg,#f3f7f2_0%,#f9efe3_45%,#e9f2f8_100%)] flex items-center justify-center p-6">
      <div className="w-full max-w-5xl grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-stretch">
        <div className="rounded-3xl bg-white/70 backdrop-blur border border-white shadow-[0_25px_80px_rgba(15,23,42,0.12)] p-10 flex flex-col justify-between">
          <div>
            <div className="inline-flex items-center gap-3 rounded-full bg-slate-900 text-white px-4 py-2 text-sm">
              <Building2 className="h-4 w-4" />
              百货柜位管理系统
            </div>
            <h1 className="mt-8 text-4xl font-bold tracking-tight text-slate-900">先用用户名密码登录，看整体配置效果。</h1>
            <p className="mt-4 text-lg leading-8 text-slate-600">
              当前已接通最小可用登录链路。默认管理员会在系统无用户时自动生成，方便你先验证账号、角色、部门和数据范围配置页。
            </p>
          </div>
          <div className="grid sm:grid-cols-3 gap-4 text-sm">
            <div className="rounded-2xl bg-slate-50 border p-4">
              <div className="font-medium text-slate-900">账号主体</div>
              <div className="mt-2 text-slate-600">统一用户表，后续可直接接企业微信身份绑定。</div>
            </div>
            <div className="rounded-2xl bg-slate-50 border p-4">
              <div className="font-medium text-slate-900">权限模型</div>
              <div className="mt-2 text-slate-600">角色、权限码、部门归属、数据策略都已建表。</div>
            </div>
            <div className="rounded-2xl bg-slate-50 border p-4">
              <div className="font-medium text-slate-900">默认账号</div>
              <div className="mt-2 text-slate-600">`admin / lampo123`</div>
            </div>
          </div>
        </div>

        <Card className="border-0 shadow-[0_25px_80px_rgba(15,23,42,0.16)] rounded-3xl">
          <CardHeader className="space-y-3 pb-4">
            <CardTitle className="text-2xl">登录</CardTitle>
            <CardDescription>先用默认管理员账号登录，进入系统配置中心查看效果。</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <Label htmlFor="username">用户名</Label>
                <div className="relative">
                  <UserRound className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input id="username" className="pl-10 h-11" value={username} onChange={(e) => setUsername(e.target.value)} />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">密码</Label>
                <div className="relative">
                  <LockKeyhole className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input id="password" type="password" className="pl-10 h-11" value={password} onChange={(e) => setPassword(e.target.value)} />
                </div>
              </div>

              {error ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              ) : null}

              <Button type="submit" className="w-full h-11 text-base" disabled={submitting}>
                {submitting ? "登录中..." : "登录"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
