import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  ArrowLeft,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  FileSearch,
  FileText,
  Home,
  Loader2,
  LogOut,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useLocation } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/contexts/AuthContext";
import { useModuleAccessLog } from "@/hooks/use-module-access-log";
import {
  getContractDisplayEndDate,
  useContractDetail,
  useContractFilterOptions,
  useContractsList,
  type ContractListItem,
} from "@/hooks/useContracts";
import { canAccessModule } from "@/lib/module-permissions";

const PAGE_SIZE = 30;
function formatDate(value?: string | null) {
  return value ? value.slice(0, 10) : "-";
}

function formatMoney(value?: number | null) {
  if (value == null || !Number.isFinite(Number(value))) return "-";
  return Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function formatPercent(value?: number | null) {
  if (value == null || !Number.isFinite(Number(value))) return "-";
  const numeric = Number(value);
  return `${(Math.abs(numeric) <= 1 ? numeric * 100 : numeric).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}%`;
}

function formatContractRates(values: Array<number | null | undefined>) {
  const rates = values
    .map((value, index) => value == null ? null : `${index + 1}档 ${formatPercent(value)}`)
    .filter((value): value is string => Boolean(value));
  return rates.join(" / ") || "-";
}

function formatSettlementMethod(value?: string | null) {
  const normalized = value?.trim().toUpperCase();
  if (!normalized) return "-";
  if (normalized === "0") return "一次";
  if (normalized === "1") return "每次";
  return value;
}

function statusClassName(status?: string | null) {
  switch ((status || "").trim().toUpperCase()) {
    case "Y":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "A":
      return "border-blue-200 bg-blue-50 text-blue-700";
    case "B":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "Q":
      return "border-slate-200 bg-slate-100 text-slate-600";
    case "S":
    case "N":
      return "border-rose-200 bg-rose-50 text-rose-700";
    default:
      return "border-slate-200 bg-white text-slate-600";
  }
}

function displayText(...values: Array<string | number | null | undefined>) {
  return values
    .map((value) => String(value ?? "").trim())
    .filter(Boolean)
    .join(" ") || "-";
}

function DetailSection({ title, count, children }: { title: string; count?: number; children: ReactNode }) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
        {typeof count === "number" ? <Badge variant="outline">{count}</Badge> : null}
      </div>
      {children}
    </section>
  );
}

function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr] gap-3 border-b border-slate-100 py-2.5 last:border-0">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="min-w-0 break-words text-right text-xs font-medium text-slate-800">{value || "-"}</div>
    </div>
  );
}

function ContractCard({ item, onClick }: { item: ContractListItem; onClick: () => void }) {
  const title = item.cmtitle || item.cmobject || item.supplier_name || item.cmppname || "未命名合同";
  const range = [item.cmeffdate || item.range_start_date, getContractDisplayEndDate(item)];
  return (
    <button
      type="button"
      className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition active:scale-[0.99] active:bg-slate-50"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="truncate text-[11px] font-medium tracking-wide text-slate-400">{item.cmcontno}</div>
          <div className="mt-1 line-clamp-2 text-sm font-semibold leading-5 text-slate-950">{title}</div>
        </div>
        <Badge variant="outline" className={`shrink-0 ${statusClassName(item.cmstatus)}`}>
          {item.status_label || item.cmstatus || "未知"}
        </Badge>
      </div>

      <div className="mt-3 space-y-2 text-xs text-slate-500">
        <div className="flex items-start gap-2">
          <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-600" />
          <span className="line-clamp-2">{displayText(item.cmsupid, item.supplier_name)}</span>
        </div>
        <div className="flex items-center gap-2">
          <CalendarDays className="h-3.5 w-3.5 shrink-0 text-teal-600" />
          <span>{formatDate(range[0])} 至 {formatDate(range[1])}</span>
        </div>
        <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-50 px-3 py-2">
          <div className="min-w-0">
            <div className="text-[10px] text-slate-400">部门 / 柜组</div>
            <div className="mt-0.5 truncate font-medium text-slate-700">
              {item.department_names || item.department_codes || item.group_names || item.group_codes || "-"}
            </div>
          </div>
          <div className="min-w-0 text-right">
            <div className="text-[10px] text-slate-400">合同面积</div>
            <div className="mt-0.5 truncate font-medium text-slate-700">
              {item.contract_area == null ? "-" : `${formatMoney(item.contract_area)} ㎡`}
            </div>
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-end gap-1 text-xs font-medium text-teal-700">
        查看合同明细 <ChevronRight className="h-4 w-4" />
      </div>
    </button>
  );
}

export default function MobileContractsPage() {
  const { user, menuUser, logout } = useAuth();
  const [, setLocation] = useLocation();
  const hasAccess = canAccessModule(menuUser, "mobile-contracts");
  const [draftKeyword, setDraftKeyword] = useState("");
  const [keyword, setKeyword] = useState("");
  const [storeCode, setStoreCode] = useState("ALL");
  const [departmentCode, setDepartmentCode] = useState("ALL");
  const [page, setPage] = useState(0);
  const [selectedContractNo, setSelectedContractNo] = useState<string | undefined>();

  const { recordQuery } = useModuleAccessLog({
    moduleId: "mobile-contracts",
    moduleName: "手机端合同台账",
    clientType: "mobile",
    enabled: hasAccess,
    initialQueryConditions: {
      query_type: "contract",
      store_code: "全部",
      department_code: "全部",
      page: 1,
    },
  });

  const contractsQuery = useContractsList({
    keyword,
    storeCode,
    departmentCode,
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,
    enabled: hasAccess,
  });
  const filterOptionsQuery = useContractFilterOptions(hasAccess);
  const contractDetailQuery = useContractDetail(selectedContractNo, hasAccess);
  const items = useMemo(() => contractsQuery.data?.items ?? [], [contractsQuery.data?.items]);

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    const nextKeyword = draftKeyword.trim();
    setPage(0);
    setKeyword(nextKeyword);
    recordQuery({
      query_type: "contract",
      keyword: nextKeyword,
      store_code: storeCode === "ALL" ? "全部" : storeCode,
      department_code: departmentCode === "ALL" ? "全部" : departmentCode,
      page: 1,
    });
  };

  if (!hasAccess) {
    return (
      <main className="min-h-[100dvh] bg-slate-50 p-5">
        <Card className="mx-auto mt-16 max-w-md rounded-3xl">
          <CardContent className="p-6 text-center">
            <ShieldCheck className="mx-auto h-10 w-10 text-slate-400" />
            <h1 className="mt-4 text-lg font-semibold">暂无合同查看权限</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">请联系管理员同时开通“手机端合同台账”和“查看合同”权限。</p>
            <div className="mt-5 flex justify-center gap-2">
              <Button variant="outline" onClick={() => setLocation("/mobile")}><Home className="mr-2 h-4 w-4" />返回首页</Button>
              <Button variant="outline" onClick={() => logout()}>退出登录</Button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-[100dvh] bg-slate-100 pb-[max(1rem,env(safe-area-inset-bottom))] text-slate-900">
      <header className="sticky top-0 z-20 bg-gradient-to-br from-slate-950 via-slate-900 to-teal-950 px-3 pb-3 pt-[max(.65rem,env(safe-area-inset-top))] text-white shadow-md">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0 rounded-full text-white hover:bg-white/10 hover:text-white"
              onClick={() => setLocation("/mobile")}
              aria-label="返回移动工作台"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="min-w-0">
              <div className="text-[9px] font-medium tracking-[0.14em] text-teal-200">SHOPVIEW</div>
              <h1 className="truncate text-base font-semibold">合同台账</h1>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-full text-white hover:bg-white/10 hover:text-white"
              onClick={() => contractsQuery.refetch()}
              aria-label="刷新合同"
            >
              <RefreshCw className={`h-4 w-4 ${contractsQuery.isFetching ? "animate-spin" : ""}`} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-full text-white hover:bg-white/10 hover:text-white"
              onClick={() => logout()}
              aria-label="退出登录"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="mt-1 pl-10 text-[10px] text-slate-300">{user?.real_name || user?.username} · 当前账号权限范围</div>
      </header>

      <div className="mx-auto max-w-xl space-y-3 px-3 pt-3">
        <Card className="rounded-2xl border-0 shadow-sm">
          <CardContent className="space-y-3 p-3">
            <form className="flex gap-2" onSubmit={submitSearch}>
              <div className="relative min-w-0 flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  value={draftKeyword}
                  onChange={(event) => setDraftKeyword(event.target.value)}
                  className="h-10 rounded-xl pl-9 text-sm"
                  placeholder="合同号、供应商、品牌、柜组"
                  aria-label="搜索合同"
                />
              </div>
              <Button type="submit" className="h-10 rounded-xl px-4">查询</Button>
            </form>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-[10px] text-slate-500">门店</Label>
                <Select
                  value={storeCode}
                  onValueChange={(value) => {
                    recordQuery({
                      query_type: "contract",
                      keyword,
                      store_code: value === "ALL" ? "全部" : value,
                      department_code: departmentCode === "ALL" ? "全部" : departmentCode,
                      page: 1,
                    });
                    setStoreCode(value);
                    setPage(0);
                  }}
                >
                  <SelectTrigger className="h-9 rounded-xl text-xs"><SelectValue placeholder="全部门店" /></SelectTrigger>
                  <SelectContent className="z-50 bg-white">
                    <SelectItem value="ALL">全部门店</SelectItem>
                    {(filterOptionsQuery.data?.stores ?? []).map((option) => (
                      <SelectItem key={option.store_code} value={option.store_code}>
                        {displayText(option.store_code, option.store_name)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] text-slate-500">所属部门</Label>
                <Select
                  value={departmentCode}
                  onValueChange={(value) => {
                    recordQuery({
                      query_type: "contract",
                      keyword,
                      store_code: storeCode === "ALL" ? "全部" : storeCode,
                      department_code: value === "ALL" ? "全部" : value,
                      page: 1,
                    });
                    setDepartmentCode(value);
                    setPage(0);
                  }}
                >
                  <SelectTrigger className="h-9 rounded-xl text-xs"><SelectValue placeholder="全部部门" /></SelectTrigger>
                  <SelectContent className="z-50 bg-white">
                    <SelectItem value="ALL">全部部门</SelectItem>
                    {(filterOptionsQuery.data?.departments ?? []).map((option) => (
                      <SelectItem key={option.department_code} value={option.department_code}>
                        {displayText(option.department_code, option.department_name)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-between px-1 text-xs text-slate-500">
          <span>合同列表 · 第 {page + 1} 页</span>
          <span>本页 {items.length} 份</span>
        </div>

        {contractsQuery.isLoading ? (
          <div className="flex min-h-52 items-center justify-center gap-2 text-sm text-teal-700">
            <Loader2 className="h-5 w-5 animate-spin" /> 正在加载合同…
          </div>
        ) : contractsQuery.isError ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
            合同加载失败：{contractsQuery.error instanceof Error ? contractsQuery.error.message : "请稍后重试"}
          </div>
        ) : items.length ? (
          <div className="space-y-3">
            {items.map((item) => (
              <ContractCard key={item.cmcontno} item={item} onClick={() => setSelectedContractNo(item.cmcontno)} />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl bg-white px-4 py-14 text-center shadow-sm">
            <FileSearch className="mx-auto h-10 w-10 text-slate-300" />
            <div className="mt-3 text-sm font-medium text-slate-700">没有找到符合条件的合同</div>
            <div className="mt-2 text-xs text-slate-400">可调整关键词、门店或部门后重新查询。</div>
          </div>
        )}

        <div className="flex items-center justify-between py-1">
          <Button
            variant="outline"
            className="rounded-xl bg-white"
            disabled={page === 0 || contractsQuery.isFetching}
            onClick={() => setPage((value) => Math.max(0, value - 1))}
          >
            <ChevronLeft className="mr-1 h-4 w-4" />上一页
          </Button>
          <Button
            variant="outline"
            className="rounded-xl bg-white"
            disabled={items.length < PAGE_SIZE || contractsQuery.isFetching}
            onClick={() => setPage((value) => value + 1)}
          >
            下一页<ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        </div>

        <div className="flex items-center justify-center gap-2 py-2 text-xs text-slate-400">
          <ShieldCheck className="h-4 w-4" /> 与网页端共享合同权限和数据范围
        </div>
      </div>

      <Dialog open={Boolean(selectedContractNo)} onOpenChange={(open) => !open && setSelectedContractNo(undefined)}>
        <DialogContent className="max-h-[92dvh] w-[calc(100vw-1rem)] max-w-lg overflow-y-auto rounded-3xl p-4">
          <DialogHeader>
            <DialogTitle className="pr-6 text-base">合同明细 {selectedContractNo}</DialogTitle>
          </DialogHeader>

          {contractDetailQuery.isLoading ? (
            <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-teal-700">
              <Loader2 className="h-5 w-5 animate-spin" /> 正在加载合同明细…
            </div>
          ) : contractDetailQuery.isError ? (
            <div className="rounded-2xl bg-amber-50 p-4 text-sm leading-6 text-amber-800">
              合同明细加载失败：{contractDetailQuery.error instanceof Error ? contractDetailQuery.error.message : "请稍后重试"}
            </div>
          ) : contractDetailQuery.data ? (
            <div className="space-y-5 pb-2">
              <DetailSection title="合同主信息">
                <div className="rounded-2xl border border-slate-200 bg-white px-3">
                  <DetailRow
                    label="状态"
                    value={<Badge variant="outline" className={statusClassName(contractDetailQuery.data.contmain?.cmstatus)}>{contractDetailQuery.data.contmain?.status_label || "未知"}</Badge>}
                  />
                  <DetailRow label="供应商" value={displayText(contractDetailQuery.data.contmain?.cmsupid, contractDetailQuery.data.contmain?.supplier_name)} />
                  <DetailRow label="合同主题" value={contractDetailQuery.data.contmain?.cmtitle || contractDetailQuery.data.contmain?.cmobject || "-"} />
                  <DetailRow label="合同类型" value={displayText(contractDetailQuery.data.contmain?.contract_type_name, contractDetailQuery.data.contmain?.cmtype)} />
                  <DetailRow label="品牌 / 品类" value={displayText(contractDetailQuery.data.contmain?.cmppname, contractDetailQuery.data.contmain?.cmcatname)} />
                  <DetailRow label="生效期限" value={`${formatDate(contractDetailQuery.data.contmain?.cmeffdate)} 至 ${formatDate(getContractDisplayEndDate(contractDetailQuery.data.contmain))}`} />
                  <DetailRow label="合同金额" value={formatMoney(contractDetailQuery.data.contmain?.cmmoney)} />
                  <DetailRow label="联系人" value={displayText(contractDetailQuery.data.contmain?.cmcontact, contractDetailQuery.data.contmain?.cmtel)} />
                </div>
              </DetailSection>

              <DetailSection title="经营范围" count={contractDetailQuery.data.counts.contmanaframe}>
                <div className="space-y-2">
                  {contractDetailQuery.data.contmanaframe.map((row, index) => (
                    <div key={`${row.cmfmfid}:${index}`} className="rounded-2xl bg-slate-50 p-3 text-xs">
                      <div className="font-semibold text-slate-900">{displayText(row.cmfmfid, row.group_name)}</div>
                      <div className="mt-2 grid grid-cols-2 gap-2 text-slate-500">
                        <span>品牌：{row.cmfbrand || "-"}</span>
                        <span className="text-right">面积：{row.cmfjzmj == null ? "-" : `${formatMoney(row.cmfjzmj)} ㎡`}</span>
                        <span className="col-span-2">合同扣点：{formatContractRates([
                          row.cmfnum1,
                          row.cmfnum2,
                          row.cmfnum3,
                          row.cmfnum4,
                          row.cmfnum5,
                        ])}</span>
                        <span className="col-span-2">期限：{formatDate(row.cmfeffdate)} 至 {formatDate(row.cmflapdate)}</span>
                      </div>
                    </div>
                  ))}
                  {!contractDetailQuery.data.contmanaframe.length ? <div className="text-xs text-slate-400">暂无经营范围明细。</div> : null}
                </div>
              </DetailSection>

              <DetailSection
                title="收费条款"
                count={contractDetailQuery.data.counts.contcyclist + contractDetailQuery.data.counts.contsupcharge}
              >
                <div className="space-y-2">
                  {contractDetailQuery.data.contcyclist.map((row) => (
                    <div key={`cycle:${row.cclseqno}`} className="rounded-2xl bg-slate-50 p-3 text-xs">
                      <div className="font-semibold text-slate-900">{row.cclitemname || row.cclitemid || "周期费用"}</div>
                      <div className="mt-1 text-slate-500">单价 {formatMoney(row.cclitemprice)} · 合计 {formatMoney(row.cclsumamount)}</div>
                    </div>
                  ))}
                  {contractDetailQuery.data.contsupcharge.map((row) => (
                    <div key={`charge:${row.cscrowno}`} className="rounded-2xl bg-slate-50 p-3 text-xs">
                      <div className="font-semibold text-slate-900">{row.cscchargename || row.cscchargecode || "附加费用"}</div>
                      <div className="mt-1 text-slate-500">取值 {formatMoney(row.cscvalue)} · 合计 {formatMoney(row.csctotal)}</div>
                      <div className="mt-1 text-slate-500">结算方式 {formatSettlementMethod(row.cscismcjs)}</div>
                    </div>
                  ))}
                  {!contractDetailQuery.data.contcyclist.length && !contractDetailQuery.data.contsupcharge.length ? (
                    <div className="text-xs text-slate-400">暂无收费条款。</div>
                  ) : null}
                </div>
              </DetailSection>

              <DetailSection title="保底条款" count={contractDetailQuery.data.counts.contbd}>
                <div className="space-y-2">
                  {contractDetailQuery.data.contbd.map((row) => (
                    <div key={`${row.cbseqno}:${row.cbmfid}`} className="rounded-2xl border border-slate-200 p-3 text-xs">
                      <div className="font-semibold text-slate-900">{displayText(row.cbmfid, row.group_name)}</div>
                      <div className="mt-2 grid grid-cols-2 gap-2 text-slate-500">
                        <span>保底额：{formatMoney(row.cbsum)}</span>
                        <span className="text-right">扣率：{formatPercent(row.cbrate)}</span>
                        <span>保底毛利：{formatMoney(row.cbprofit)}</span>
                        <span className="text-right">区间销售：{formatMoney(row.xssr)}</span>
                        <span className="col-span-2">期限：{formatDate(row.cbeffdate)} 至 {formatDate(row.cblapdate)}</span>
                      </div>
                    </div>
                  ))}
                  {!contractDetailQuery.data.contbd.length ? <div className="text-xs text-slate-400">暂无保底条款。</div> : null}
                </div>
              </DetailSection>

            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </main>
  );
}
