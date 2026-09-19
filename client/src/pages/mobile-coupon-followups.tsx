import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CalendarDays, CheckCircle2, Gift, Home, Loader2, Search, ShieldCheck, Store, Users } from "lucide-react";
import { useLocation } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/contexts/AuthContext";
import { useModuleAccessLog } from "@/hooks/use-module-access-log";
import { apiGet } from "@/lib/api";
import { canAccessModule } from "@/lib/module-permissions";

type FollowupRow = Record<string, number | string | null>;
type FollowupResponse = {
  summary: Record<string, number>;
  items: FollowupRow[];
  total: number;
  history_window: { basis: string };
};

const localMonth = () => {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
};

const money = (value: unknown) => new Intl.NumberFormat("zh-CN", {
  style: "currency",
  currency: "CNY",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
}).format(Number(value || 0));

const number = (value: unknown) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(Number(value || 0));

const statusTone = (status: unknown) => {
  if (status === "REDEEMED") return "bg-emerald-100 text-emerald-800 hover:bg-emerald-100";
  if (status === "VISITED_NOT_REDEEMED") return "bg-amber-100 text-amber-800 hover:bg-amber-100";
  if (status === "UNASSIGNED_BRAND" || status === "UNASSIGNED_MANAGER") return "bg-rose-100 text-rose-800 hover:bg-rose-100";
  return "bg-slate-100 text-slate-700 hover:bg-slate-100";
};

function errorText(error: unknown) {
  return error instanceof Error ? error.message : "查询失败，请稍后重试";
}

export default function MobileCouponFollowupsPage() {
  const { menuUser } = useAuth();
  const [, setLocation] = useLocation();
  const hasAccess = canAccessModule(menuUser, "mobile-coupon-followups");
  const [periodMonth, setPeriodMonth] = useState(localMonth);
  const [statusCode, setStatusCode] = useState("ALL");
  const [keywordDraft, setKeywordDraft] = useState("");
  const [keyword, setKeyword] = useState("");

  const { recordQuery } = useModuleAccessLog({
    moduleId: "mobile-coupon-followups",
    moduleName: "手机端C券会员跟进",
    clientType: "mobile",
    enabled: hasAccess,
  });

  const params = new URLSearchParams({
    period_month: periodMonth,
    status_code: statusCode,
    keyword,
    limit: "1000",
    offset: "0",
  }).toString();
  const followupsQuery = useQuery<FollowupResponse>({
    queryKey: ["mobile-coupon-followups", periodMonth, statusCode, keyword],
    queryFn: () => apiGet(`/api/activity-analysis/birthday-coupon/followups/mobile?${params}`),
    enabled: hasAccess,
    staleTime: 30_000,
  });

  const applySearch = () => {
    setKeyword(keywordDraft.trim());
    void recordQuery({ query_type: "c_coupon_member_followup", period_month: periodMonth, status_code: statusCode });
  };

  if (!hasAccess) {
    return <main className="grid min-h-[100dvh] place-items-center bg-slate-100 p-5"><Card className="w-full max-w-md rounded-3xl border-0 shadow-lg"><CardContent className="p-7 text-center">
      <ShieldCheck className="mx-auto h-10 w-10 text-slate-400" /><h1 className="mt-4 text-lg font-semibold">暂无C券会员跟进权限</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">请联系管理员维护您负责的品牌柜组，系统会自动开通对应的手机跟进权限。</p>
      <Button variant="outline" className="mt-5" onClick={() => setLocation("/mobile")}><Home className="mr-2 h-4 w-4" />返回首页</Button>
    </CardContent></Card></main>;
  }

  return (
    <main className="min-h-[100dvh] bg-slate-100 pb-[max(1.25rem,env(safe-area-inset-bottom))] text-slate-900">
      <header className="sticky top-0 z-20 bg-gradient-to-br from-slate-950 via-slate-900 to-violet-950 px-4 pb-5 pt-[max(.75rem,env(safe-area-inset-top))] text-white shadow-md">
        <div className="flex items-center gap-3"><Button variant="ghost" size="icon" className="rounded-full text-white hover:bg-white/10 hover:text-white" onClick={() => setLocation("/mobile")}><ArrowLeft className="h-5 w-5" /></Button>
          <div><div className="text-[10px] tracking-[.16em] text-violet-200">C COUPON FOLLOW-UP</div><h1 className="text-lg font-semibold">会员跟进</h1></div>
        </div>
      </header>

      <div className="mx-auto max-w-xl space-y-4 px-4 pt-4">
        <Card className="rounded-3xl border-0 shadow-sm"><CardContent className="space-y-3 p-4">
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs font-medium text-slate-600">C券发放月</label><Input type="month" className="mt-1" value={periodMonth} onChange={(event) => setPeriodMonth(event.target.value)} /></div>
            <div><label className="text-xs font-medium text-slate-600">状态</label><Select value={statusCode} onValueChange={setStatusCode}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent>
              <SelectItem value="ALL">全部</SelectItem><SelectItem value="NOT_VISITED">未到店</SelectItem><SelectItem value="VISITED_NOT_REDEEMED">已到店未用券</SelectItem><SelectItem value="REDEEMED">已用券</SelectItem><SelectItem value="REDEEMED_RETURNED">用券后已退</SelectItem>
            </SelectContent></Select></div>
          </div>
          <form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); applySearch(); }}><div className="relative flex-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><Input className="pl-9" value={keywordDraft} onChange={(event) => setKeywordDraft(event.target.value)} placeholder="搜索会员或负责品牌" /></div><Button type="submit">查询</Button></form>
        </CardContent></Card>

        {followupsQuery.data ? <div className="grid grid-cols-3 gap-2">
          <Card className="rounded-2xl border-0"><CardContent className="p-3"><Users className="h-4 w-4 text-violet-600" /><p className="mt-2 text-xl font-semibold">{number(followupsQuery.data.summary.target_member_count)}</p><p className="text-[11px] text-slate-500">需跟进</p></CardContent></Card>
          <Card className="rounded-2xl border-0"><CardContent className="p-3"><Store className="h-4 w-4 text-amber-600" /><p className="mt-2 text-xl font-semibold">{number(followupsQuery.data.summary.visited_member_count)}</p><p className="text-[11px] text-slate-500">已到店</p></CardContent></Card>
          <Card className="rounded-2xl border-0"><CardContent className="p-3"><Gift className="h-4 w-4 text-emerald-600" /><p className="mt-2 text-xl font-semibold">{number(followupsQuery.data.summary.redeemed_member_count)}</p><p className="text-[11px] text-slate-500">已用券</p></CardContent></Card>
        </div> : null}

        {followupsQuery.isLoading ? <Card className="rounded-3xl border-0"><CardContent className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500"><Loader2 className="h-5 w-5 animate-spin" />正在读取我的跟进会员…</CardContent></Card>
          : followupsQuery.isError ? <Card className="rounded-3xl border-rose-200 bg-rose-50"><CardContent className="p-4 text-sm text-rose-700">{errorText(followupsQuery.error)}</CardContent></Card>
          : followupsQuery.data?.items.length ? <div className="space-y-3">{followupsQuery.data.items.map((row) => <Card key={String(row.member_no)} className="rounded-3xl border-0 shadow-sm"><CardContent className="p-4">
            <div className="flex items-start justify-between gap-3"><div><p className="font-mono text-sm font-semibold">{String(row.masked_member_no || "—")}</p><p className="mt-1 text-xs text-slate-500">{String(row.masked_customer_name || "—")} · {String(row.customer_level || "—")}</p></div><Badge className={statusTone(row.followup_status)}>{String(row.followup_status_label || "待核对")}</Badge></div>
            <div className="mt-4 rounded-2xl bg-slate-50 p-3"><p className="text-xs text-slate-500">负责品牌柜组</p><p className="mt-1 font-medium">{String(row.followup_group_name || "待分配")}</p><p className="mt-1 text-xs text-slate-500">{String(row.department_name || "未归属部门")}</p></div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center"><div><p className="text-xs text-slate-500">历史消费</p><p className="mt-1 text-sm font-semibold">{money(row.history_sales_amount)}</p></div><div><p className="text-xs text-slate-500">当月消费</p><p className="mt-1 text-sm font-semibold">{money(row.current_sales_amount)}</p></div><div><p className="text-xs text-slate-500">C券核销</p><p className="mt-1 text-sm font-semibold">{money(row.net_redeemed_amount)}</p></div></div>
            <div className="mt-3 flex items-center gap-2 border-t pt-3 text-xs text-slate-500">{Number(row.current_ticket_count || 0) > 0 ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <CalendarDays className="h-4 w-4" />}当月 {number(row.current_ticket_count)} 张正向消费小票</div>
          </CardContent></Card>)}</div>
          : <Card className="rounded-3xl border-0"><CardContent className="py-14 text-center text-sm text-slate-500">当前条件下没有需要跟进的会员</CardContent></Card>}
      </div>
    </main>
  );
}
