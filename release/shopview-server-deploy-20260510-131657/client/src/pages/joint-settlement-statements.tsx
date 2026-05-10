import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useJointSettlementDetail,
  useJointSettlementList,
  type JointSettlementListItem,
} from "@/hooks/useErpJointSettlements";
import { cn } from "@/lib/utils";

function fmtMoney(v: unknown): string {
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(v: unknown): string {
  if (v == null || v === "") return "—";
  const s = String(v);
  return s.length >= 10 ? s.slice(0, 10) : s;
}

/** 发生月 sscfsmon：常见为 YYYYMM 数值或字符串 */
function fmtFsMon(v: unknown): string {
  if (v == null || v === "") return "—";
  const s = String(v).replace(/\D/g, "");
  if (s.length === 6) return `${s.slice(0, 4)}-${s.slice(4, 6)}`;
  return String(v);
}

/** supsettledet.ssdn80 税率展示（常见为百分点数值） */
function fmtTaxSsdn80(v: unknown): string {
  if (v == null || v === "") return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return String(v);
  if (n >= 0 && n <= 1) return `${(n * 100).toFixed(2)}%`;
  return `${n}%`;
}

/** ERP 标志位常见取值，未知时原样显示 */
function docFlagLabel(code: string | null | undefined): string {
  if (!code) return "—";
  const m: Record<string, string> = {
    M: "生成",
    Y: "审核",
    N: "未审",
    E: "收款完成",
  };
  return m[code] ?? code;
}

function payFlagLabel(code: string | null | undefined): string {
  if (!code) return "—";
  const m: Record<string, string> = {
    Y: "已付款",
    N: "未付款",
    P: "部分付款",
  };
  return m[code] ?? code;
}

/** ERP 结算单表头（与后端 header_display 字段对齐） */
function erpHeaderDisplayPairs(h: Record<string, unknown>): { label: string; value: string }[] {
  const g = (k: string) => h[k];
  const fb = g("erp_header_fallback") === true;
  return [
    { label: "结算单号", value: String(g("sshbillno") ?? "—") },
    { label: "付款单号", value: String(g("sphbillno") ?? "—") },
    { label: "付款起始日期", value: fmtDate(g("bgdate")) },
    { label: "付款截止日期", value: fmtDate(g("eddate")) },
    { label: "付款批次·付款单关联", value: String(g("pb_paybillno") ?? "—") },
    { label: "付款批次·单据号", value: String(g("pb_billno") ?? "—") },
    { label: "供应商", value: String(g("supplier_display") ?? "—") },
    { label: "部门", value: String(g("dept_display") ?? "—") },
    { label: "经营方式", value: String(g("operation_mode_label") ?? "—") },
    { label: "税号", value: String(g("sphtaxno") ?? "—") },
    { label: "开户银行", value: String(g("sphbank") ?? "—") },
    { label: "银行帐号", value: String(g("sphaccntno") ?? "—") },
    { label: "销售收入(paybatch 汇总)", value: fmtMoney(g("xssr")) },
    { label: "开票金额(paybatch 汇总)", value: fmtMoney(g("kp_amount")) },
    { label: "费用(supsetcharge 按付款单汇总)", value: fmtMoney(g("fee_amount")) },
    { label: "实际应付", value: fmtMoney(g("sphmoney")) },
    { label: "人民币大写", value: String(g("sphmoneyupper") ?? "—") },
    { label: "上期转入", value: fmtMoney(g("sshlastye")) },
    { label: "转入下期", value: fmtMoney(g("sshthisye")) },
    { label: "结算调整", value: fmtMoney(g("sshsetadj")) },
    { label: "预付款", value: fmtMoney(g("sshyfkje")) },
    { label: "商场全称", value: String(g("mktname") ?? "—") },
    { label: "商场地址", value: String(g("mktads") ?? "—") },
    { label: "商场电话", value: String(g("telph") ?? "—") },
    { label: "商场开户银行", value: String(g("sphmktbank") ?? "—") },
    { label: "商场银行账号", value: String(g("sphmktaccntno") ?? "—") },
    { label: "商场税号", value: String(g("sphmkttaxno") ?? "—") },
    { label: "付款日期", value: fmtDate(g("sphpaydate")) },
    { label: "计划付款日期", value: fmtDate(g("sshplanpaydate")) },
    { label: "付款标志", value: String(g("payment_flag_label") ?? "—") },
    { label: "录入人(编码)", value: String(g("inputor_code") ?? "—") },
    { label: "录入日期", value: fmtDate(g("inputdate")) },
    { label: "审核人(编码)", value: String(g("auditor_code") ?? "—") },
    { label: "审核日期", value: fmtDate(g("auditdate")) },
    { label: "付款方式", value: String(g("paymode_display") ?? "—") },
    ...(fb
      ? [{ label: "说明", value: "无 suppayhead 表或未能关联付款头，以下为 supsettlehead 降级字段" }]
      : []),
  ];
}

function settlementHeadPairs(head: Record<string, unknown>): { label: string; value: string }[] {
  const g = (k: string) => head[k];
  return [
    { label: "结算单号", value: String(g("sshbillno") ?? "—") },
    { label: "单据号(paybatch·pbbillno)", value: String(g("paybatch_pbbillno") ?? "—") },
    { label: "门店", value: String(g("sshmkt") ?? "—") },
    { label: "单据状态", value: docFlagLabel(g("sshflag") as string) },
    { label: "付款标志", value: payFlagLabel(g("sshpayflag") as string) },
    { label: "合同号", value: String(g("sshcontno") ?? "—") },
    { label: "供应商", value: String(g("sshsupid") ?? "—") },
    { label: "经营方式", value: String(g("sshwmid") ?? "—") },
    { label: "制单日期", value: fmtDate(g("sshdate")) },
    { label: "上次结算日期", value: fmtDate(g("sshlastdate")) },
    { label: "本次结算日期", value: fmtDate(g("sshthisdate")) },
    { label: "终止/到期日期", value: fmtDate(g("sshenddate")) },
    { label: "销售收入(明细汇总)", value: fmtMoney(g("sales_revenue_sum")) },
    { label: "扣款合计", value: fmtMoney(g("sshtotkk")) },
    { label: "结算调整", value: fmtMoney(g("sshsetadj")) },
    { label: "调整金额", value: fmtMoney(g("sshadjustje")) },
    { label: "应付金额合计", value: fmtMoney(g("sshtotyfje")) },
    { label: "预付款金额", value: fmtMoney(g("sshyfkje")) },
    { label: "结算金额", value: fmtMoney(g("sshsetje")) },
    { label: "实际付款", value: fmtMoney(g("sshsjfkje")) },
    { label: "发票号", value: String(g("sshinvno") ?? "—") },
    { label: "付款单号", value: String(g("sshpayno") ?? "—") },
    { label: "计划付款日", value: fmtDate(g("sshplanpaydate")) },
    { label: "付款审核日", value: fmtDate(g("paydate")) },
    { label: "开户银行", value: String(g("sshbank") ?? "—") },
    { label: "银行账号", value: String(g("sshaccntno") ?? "—") },
    { label: "纳税号", value: String(g("sshtaxno") ?? "—") },
    { label: "制单人", value: String(g("inputor") ?? "—") },
    { label: "制单日期(录入)", value: fmtDate(g("inputdate")) },
    { label: "审核人", value: String(g("auditor") ?? "—") },
    { label: "审核日期", value: fmtDate(g("auditdate")) },
    { label: "备注", value: String(g("sshvc3") ?? "—") },
  ];
}

export default function JointSettlementStatementsPage() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [mkt, setMkt] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [keyword, setKeyword] = useState("");

  const [applied, setApplied] = useState({
    mkt: "",
    date_from: "",
    date_to: "",
    keyword: "",
  });

  /** 进入页面不自动拉列表，仅在点击「查询」后为 true，减轻首屏卡顿 */
  const [listFetchEnabled, setListFetchEnabled] = useState(false);

  const listParams = useMemo(
    () => ({
      page,
      page_size: pageSize,
      mkt: applied.mkt || undefined,
      date_from: applied.date_from || undefined,
      date_to: applied.date_to || undefined,
      keyword: applied.keyword || undefined,
    }),
    [page, pageSize, applied],
  );

  const listQuery = useJointSettlementList(listParams, listFetchEnabled);

  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedBillNo, setSelectedBillNo] = useState<string | null>(null);
  const detailQuery = useJointSettlementDetail(detailOpen ? selectedBillNo : null);

  const totalPages = useMemo(() => {
    const t = listQuery.data?.total ?? 0;
    return Math.max(1, Math.ceil(t / pageSize));
  }, [listQuery.data?.total, pageSize]);

  const applyFilters = () => {
    setListFetchEnabled(true);
    setPage(1);
    setApplied({
      mkt,
      date_from: dateFrom,
      date_to: dateTo,
      keyword,
    });
  };

  const openDetail = (row: JointSettlementListItem) => {
    setSelectedBillNo(row.sshbillno);
    setDetailOpen(true);
  };

  const headForSheet = useMemo(() => {
    const h = detailQuery.data?.head;
    if (!h) return null;
    const copy = { ...h } as Record<string, unknown>;
    const sumSr = (detailQuery.data?.lines ?? []).reduce((s, line) => {
      const v = line.sdtxssr;
      const n = typeof v === "number" ? v : Number(v);
      return s + (Number.isFinite(n) ? n : 0);
    }, 0);
    const sumFee = (detailQuery.data?.charges ?? []).reduce((s, ch) => {
      const v = ch.sscmoney;
      const n = typeof v === "number" ? v : Number(v);
      return s + (Number.isFinite(n) ? n : 0);
    }, 0);
    copy.sales_revenue_sum = sumSr;
    copy.fee_sum_from_charges = sumFee;
    const pb = detailQuery.data?.paybatch ?? [];
    const primaryPb =
      pb.find((r) => String(r.pbbilltype ?? "").trim() === "J") ?? pb[0];
    copy.paybatch_pbbillno = primaryPb?.pbbillno ?? null;
    return copy;
  }, [detailQuery.data]);

  /** 明细弹窗「表头」：有 ERP 付款头展示则用之，否则主表 supsettlehead 字段 */
  const detailHeaderPairs = useMemo(() => {
    if (!detailQuery.data?.head || !headForSheet) return null;
    const hd = detailQuery.data.header_display as Record<string, unknown> | undefined;
    if (hd && Object.keys(hd).length > 0) return erpHeaderDisplayPairs(hd);
    return settlementHeadPairs(headForSheet);
  }, [detailQuery.data, headForSheet]);

  return (
    <div className="p-6 space-y-6" data-testid="joint-settlement-page">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">联营结算单管理</h1>
        <p className="text-sm text-muted-foreground mt-1">
          明细仅展示三块：表头、销售、费用。列表按数据权限中的「柜组」维度过滤（ERP 柜组编码须与 supsettlehead /
          suppayhead 解析出的柜组一致）；明细接口需登录且具备{" "}
          <code className="text-xs bg-slate-100 px-1 rounded">settlement.view</code>
          ；用户「工号」请维护在账号资料（users.employee_no），数据范围在系统管理中按柜组编码配置。
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">筛选</CardTitle>
          <CardDescription>
            按门店、制单日期、关键词查询（关键词含结算单号、合同、供应商、
            <code className="text-xs bg-slate-100 px-1 rounded">paybatch.pbbillno</code>{" "}
            单据号）。首次进入不会自动请求，请点击「查询」加载列表。
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 items-end">
          <div className="space-y-2">
            <Label htmlFor="js-mkt">门店</Label>
            <Input id="js-mkt" placeholder="编码或片段" value={mkt} onChange={(e) => setMkt(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="js-from">制单日期起</Label>
            <Input id="js-from" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="js-to">制单日期止</Label>
            <Input id="js-to" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="js-kw">关键词</Label>
            <Input
              id="js-kw"
              placeholder="结算单号 / 合同号 / 供应商 / 单据号(pbbillno)"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <Button type="button" className="w-full sm:w-auto" onClick={applyFilters}>
            查询
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-2">
          <div>
            <CardTitle className="text-base">单据列表</CardTitle>
            <CardDescription>
              {listFetchEnabled ? (
                <>
                  共 {listQuery.data?.total ?? 0} 条 · 第 {page} / {totalPages} 页
                </>
              ) : (
                <>尚未查询 · 设置条件后点击「查询」</>
              )}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!listFetchEnabled || page <= 1 || listQuery.isFetching}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              上一页
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!listFetchEnabled || page >= totalPages || listQuery.isFetching}
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
            </Button>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="whitespace-nowrap w-10">序号</TableHead>
                <TableHead className="whitespace-nowrap">门店</TableHead>
                <TableHead className="whitespace-nowrap">结算单号</TableHead>
                <TableHead className="whitespace-nowrap">单据号</TableHead>
                <TableHead className="whitespace-nowrap min-w-[140px]">部门(付款头)</TableHead>
                <TableHead className="whitespace-nowrap">单据状态</TableHead>
                <TableHead className="whitespace-nowrap">付款标志</TableHead>
                <TableHead className="whitespace-nowrap">合同号</TableHead>
                <TableHead className="whitespace-nowrap min-w-[140px]">供应商</TableHead>
                <TableHead className="whitespace-nowrap">经营方式</TableHead>
                <TableHead className="whitespace-nowrap">制单日期</TableHead>
                <TableHead className="whitespace-nowrap">上次结算</TableHead>
                <TableHead className="whitespace-nowrap">本次结算</TableHead>
                <TableHead className="whitespace-nowrap">终止结算</TableHead>
                <TableHead className="whitespace-nowrap">制单人</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {!listFetchEnabled ? (
                <TableRow>
                  <TableCell colSpan={15} className="text-center py-12 text-muted-foreground text-sm">
                    请点击上方「查询」加载列表（进入本页不会自动检索）。
                  </TableCell>
                </TableRow>
              ) : listQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={15} className="text-center py-12 text-muted-foreground">
                    <Loader2 className="inline h-5 w-5 animate-spin mr-2 align-middle" />
                    加载中…
                  </TableCell>
                </TableRow>
              ) : listQuery.isError ? (
                <TableRow>
                  <TableCell colSpan={15} className="text-center py-10 text-destructive text-sm">
                    <div className="font-medium mb-2">加载失败</div>
                    <div className="text-xs text-destructive/90 break-all max-w-2xl mx-auto whitespace-pre-wrap">
                      {listQuery.error instanceof Error ? listQuery.error.message : String(listQuery.error)}
                    </div>
                    <p className="text-xs text-muted-foreground mt-3 max-w-xl mx-auto">
                      本地开发：后端需运行在{" "}
                      <code className="bg-slate-100 px-1 rounded">localhost:8000</code>
                      ，通过 Vite 将{" "}
                      <code className="bg-slate-100 px-1 rounded">/api</code>{" "}
                      代理过去；数据库连接须与 Navicat 查看的是同一实例。
                    </p>
                  </TableCell>
                </TableRow>
              ) : (listQuery.data?.items ?? []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={15} className="text-center py-10 text-muted-foreground">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                (listQuery.data?.items ?? []).map((row, idx) => (
                  <TableRow
                    key={row.sshbillno}
                    className={cn("cursor-pointer hover:bg-slate-50")}
                    onClick={() => openDetail(row)}
                  >
                    <TableCell>{(page - 1) * pageSize + idx + 1}</TableCell>
                    <TableCell className="whitespace-nowrap">{row.sshmkt ?? "—"}</TableCell>
                    <TableCell className="font-mono text-xs whitespace-nowrap">{row.sshbillno}</TableCell>
                    <TableCell className="font-mono text-xs whitespace-nowrap">
                      {row.pbbillno ?? "—"}
                    </TableCell>
                    <TableCell className="text-xs max-w-[160px]" title={String(row.sphmfid ?? "")}>
                      {(row.sphmf_department_display as string | undefined) ??
                        (row.sphmfid != null && row.sphmfid !== ""
                          ? String(row.sphmfid)
                          : "—")}
                    </TableCell>
                    <TableCell>{docFlagLabel(row.sshflag)}</TableCell>
                    <TableCell>{payFlagLabel(row.sshpayflag)}</TableCell>
                    <TableCell className="whitespace-nowrap">{row.sshcontno ?? "—"}</TableCell>
                    <TableCell className="text-xs">{row.sshsupid ?? "—"}</TableCell>
                    <TableCell>{row.sshwmid ?? "—"}</TableCell>
                    <TableCell>{fmtDate(row.sshdate)}</TableCell>
                    <TableCell>{fmtDate(row.sshlastdate)}</TableCell>
                    <TableCell>{fmtDate(row.sshthisdate)}</TableCell>
                    <TableCell>{fmtDate(row.sshenddate)}</TableCell>
                    <TableCell className="text-xs max-w-[100px] truncate" title={row.inputor ?? ""}>
                      {row.inputor ?? "—"}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog
        open={detailOpen}
        onOpenChange={(o) => {
          setDetailOpen(o);
          if (!o) setSelectedBillNo(null);
        }}
      >
        <DialogContent
          className={cn(
            "flex max-h-[90vh] w-[calc(100vw-1.5rem)] max-w-5xl flex-col gap-0 overflow-hidden p-0 sm:w-full",
            "bg-white text-slate-900 border-slate-200 shadow-2xl",
          )}
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <DialogHeader className="shrink-0 space-y-1 border-b border-slate-100 px-6 py-4 text-left">
            <DialogTitle>结算单</DialogTitle>
            <DialogDescription className="font-mono text-xs text-slate-600">
              {selectedBillNo ? selectedBillNo : "请选择列表中的单据"}
            </DialogDescription>
          </DialogHeader>

          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          {detailQuery.isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground py-8 bg-white">
              <Loader2 className="h-5 w-5 animate-spin" />
              加载明细…
            </div>
          )}

          {detailQuery.isError && (
            <p className="text-sm text-destructive py-4 bg-white">无法加载明细，请稍后重试。</p>
          )}

          {detailQuery.data && headForSheet && detailHeaderPairs && (
            <div className="space-y-8 pb-4 bg-white">
              <section>
                <h3 className="text-sm font-semibold text-slate-800 mb-3">表头</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm border border-slate-200 rounded-md p-4 bg-slate-50">
                  {detailHeaderPairs.map(({ label, value }) => (
                    <div
                      key={label}
                      className="flex gap-2 justify-between border-b border-slate-100 pb-1 last:border-0"
                    >
                      <span className="text-muted-foreground shrink-0">{label}</span>
                      <span className="text-right break-all">{value}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section>
                <h3 className="text-sm font-semibold text-slate-800 mb-3">销售</h3>
                <div className="overflow-x-auto rounded-md border border-slate-200 bg-white shadow-sm">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50">
                        <TableHead className="whitespace-nowrap">付款单号</TableHead>
                        <TableHead className="whitespace-nowrap">单据号</TableHead>
                        <TableHead className="whitespace-nowrap">结算单号</TableHead>
                        <TableHead className="whitespace-nowrap">考核/销售类型</TableHead>
                        <TableHead className="whitespace-nowrap">柜组</TableHead>
                        <TableHead className="whitespace-nowrap">结算截止日</TableHead>
                        <TableHead className="whitespace-nowrap">合同号</TableHead>
                        <TableHead className="whitespace-nowrap text-right">销售收入</TableHead>
                        <TableHead className="whitespace-nowrap text-right">应开票金额</TableHead>
                        <TableHead className="whitespace-nowrap text-right">数量</TableHead>
                        <TableHead className="whitespace-nowrap text-right">税率</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(detailQuery.data.paybatch_sales ?? []).length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={11} className="text-center text-muted-foreground py-6 text-xs">
                            暂无结算单销售行（需 paybatch；若有 supsettledet 则含数量与税率）。
                          </TableCell>
                        </TableRow>
                      ) : (
                        (detailQuery.data.paybatch_sales ?? []).map((row, i) => (
                          <TableRow
                            key={`pbs-${String(row.pbseq)}-${i}-${String(row.pbbillno)}-${String(row.ssdn80)}-${String(row.ssdvc6)}`}
                            className="bg-white border-b border-slate-100"
                          >
                            <TableCell className="font-mono text-xs">{String(row.pbpaybillno ?? "—")}</TableCell>
                            <TableCell className="font-mono text-xs">{String(row.pbbillno ?? "—")}</TableCell>
                            <TableCell className="font-mono text-xs">{String(row.pbjsno ?? "—")}</TableCell>
                            <TableCell className="text-xs max-w-[140px]">
                              {String(row.ssdvc6_label ?? row.ssdvc6 ?? "—")}
                            </TableCell>
                            <TableCell className="text-xs">{String(row.pbmfid ?? "—")}</TableCell>
                            <TableCell>{fmtDate(row.pbjsedate)}</TableCell>
                            <TableCell className="text-xs whitespace-nowrap">{String(row.pbcontno ?? "—")}</TableCell>
                            <TableCell className="text-right tabular-nums">{fmtMoney(row.pbxssr)}</TableCell>
                            <TableCell className="text-right tabular-nums">{fmtMoney(row.pbkp)}</TableCell>
                            <TableCell className="text-right tabular-nums">
                              {row.sl != null && row.sl !== "" ? String(row.sl) : "—"}
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-xs">{fmtTaxSsdn80(row.ssdn80)}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                {detailQuery.data.lines.length > 0 && (
                  <div className="mt-6 overflow-x-auto rounded-md border border-slate-200 bg-white shadow-sm">
                    <p className="text-xs text-muted-foreground px-3 pt-3 mb-2">明细汇总（supsettledettot）</p>
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-slate-50">
                          <TableHead className="whitespace-nowrap">行号</TableHead>
                          <TableHead className="whitespace-nowrap">部门</TableHead>
                          <TableHead className="whitespace-nowrap">柜组</TableHead>
                          <TableHead className="whitespace-nowrap">项目编码</TableHead>
                          <TableHead className="whitespace-nowrap text-right">销售收入</TableHead>
                          <TableHead className="whitespace-nowrap text-right">结算金额</TableHead>
                          <TableHead className="whitespace-nowrap text-right">税率</TableHead>
                          <TableHead className="whitespace-nowrap min-w-[180px]">说明</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detailQuery.data.lines.map((line) => (
                          <TableRow key={String(line.sdtrowno)} className="bg-white border-b border-slate-100">
                            <TableCell>{String(line.sdtrowno ?? "")}</TableCell>
                            <TableCell className="text-xs whitespace-nowrap">{String(line.sdtdep ?? "—")}</TableCell>
                            <TableCell className="text-xs whitespace-nowrap">{String(line.sdtmfid ?? "—")}</TableCell>
                            <TableCell className="text-xs">{String(line.sdtitemcode ?? "—")}</TableCell>
                            <TableCell className="text-right tabular-nums">{fmtMoney(line.sdtxssr)}</TableCell>
                            <TableCell className="text-right tabular-nums">{fmtMoney(line.sdtamount)}</TableCell>
                            <TableCell className="text-right tabular-nums">
                              {line.sdttaxrate != null && line.sdttaxrate !== ""
                                ? `${String(line.sdttaxrate)}%`
                                : "—"}
                            </TableCell>
                            <TableCell className="text-xs max-w-[220px]">{String(line.sdtmemo ?? "—")}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </section>

              <section>
                <h3 className="text-sm font-semibold text-slate-800 mb-3">费用</h3>
                <div className="overflow-x-auto rounded-md border border-slate-200 bg-white shadow-sm">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50">
                        <TableHead className="whitespace-nowrap">行号</TableHead>
                        <TableHead className="whitespace-nowrap">付款单号</TableHead>
                        <TableHead className="whitespace-nowrap">票减</TableHead>
                        <TableHead className="whitespace-nowrap">合同号</TableHead>
                        <TableHead className="whitespace-nowrap min-w-[140px]">柜组</TableHead>
                        <TableHead className="whitespace-nowrap">发生月</TableHead>
                        <TableHead className="whitespace-nowrap">发生日期</TableHead>
                        <TableHead className="whitespace-nowrap min-w-[160px]">费用名称</TableHead>
                        <TableHead className="whitespace-nowrap text-right">金额</TableHead>
                        <TableHead className="whitespace-nowrap">费用单号</TableHead>
                        <TableHead className="whitespace-nowrap">状态</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detailQuery.data.charges.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={11} className="text-center text-muted-foreground py-6 text-xs">
                            暂无费用行（sscjsno 应对齐当前结算单号）。
                          </TableCell>
                        </TableRow>
                      ) : (
                        detailQuery.data.charges.map((ch) => (
                          <TableRow
                            key={`${String(ch.sscbillno)}-${String(ch.sscrowno)}`}
                            className="bg-white border-b border-slate-100"
                          >
                            <TableCell>{String(ch.sscrowno ?? "")}</TableCell>
                            <TableCell className="font-mono text-xs">{String(ch.sscpaybillno ?? "—")}</TableCell>
                            <TableCell className="text-xs whitespace-nowrap">
                              {String(ch.person1_label ?? ch.person1 ?? "—")}
                            </TableCell>
                            <TableCell className="text-xs whitespace-nowrap">{String(ch.ssccontno ?? "—")}</TableCell>
                            <TableCell className="text-xs max-w-[200px]">
                              {String(ch.counter_display ?? ch.sscmfid ?? "—")}
                            </TableCell>
                            <TableCell className="tabular-nums text-xs">{fmtFsMon(ch.sscfsmon)}</TableCell>
                            <TableCell>{fmtDate(ch.sscfsdate)}</TableCell>
                            <TableCell className="text-xs max-w-[220px]">
                              {String(ch.expense_name_display ?? ch.sscname ?? "—")}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">{fmtMoney(ch.sscmoney)}</TableCell>
                            <TableCell className="font-mono text-xs">{String(ch.sscbillno ?? "—")}</TableCell>
                            <TableCell className="text-xs whitespace-nowrap">
                              {String(ch.sscflag_label ?? ch.sscflag ?? "—")}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                {(detailQuery.data.charges_by_payment_bill ?? []).length > 0 && (
                  <div className="mt-6 overflow-x-auto rounded-md border border-slate-200 bg-white shadow-sm">
                    <p className="text-xs text-muted-foreground px-3 pt-3 mb-2">按付款单号（与表头付款单一致）</p>
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-slate-50">
                          <TableHead className="whitespace-nowrap">行号</TableHead>
                          <TableHead className="whitespace-nowrap">付款单号</TableHead>
                          <TableHead className="whitespace-nowrap">票减</TableHead>
                          <TableHead className="whitespace-nowrap">合同号</TableHead>
                          <TableHead className="whitespace-nowrap min-w-[140px]">柜组</TableHead>
                          <TableHead className="whitespace-nowrap">发生月</TableHead>
                          <TableHead className="whitespace-nowrap">发生日期</TableHead>
                          <TableHead className="whitespace-nowrap min-w-[160px]">费用名称</TableHead>
                          <TableHead className="whitespace-nowrap text-right">金额</TableHead>
                          <TableHead className="whitespace-nowrap">费用单号</TableHead>
                          <TableHead className="whitespace-nowrap">状态</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(detailQuery.data.charges_by_payment_bill ?? []).map((ch) => (
                          <TableRow
                            key={`pay-${String(ch.sscbillno)}-${String(ch.sscrowno)}`}
                            className="bg-white border-b border-slate-100"
                          >
                            <TableCell>{String(ch.sscrowno ?? "")}</TableCell>
                            <TableCell className="font-mono text-xs">{String(ch.sscpaybillno ?? "—")}</TableCell>
                            <TableCell className="text-xs whitespace-nowrap">
                              {String(ch.person1_label ?? ch.person1 ?? "—")}
                            </TableCell>
                            <TableCell className="text-xs whitespace-nowrap">{String(ch.ssccontno ?? "—")}</TableCell>
                            <TableCell className="text-xs max-w-[200px]">
                              {String(ch.counter_display ?? ch.sscmfid ?? "—")}
                            </TableCell>
                            <TableCell className="tabular-nums text-xs">{fmtFsMon(ch.sscfsmon)}</TableCell>
                            <TableCell>{fmtDate(ch.sscfsdate)}</TableCell>
                            <TableCell className="text-xs max-w-[220px]">
                              {String(ch.expense_name_display ?? ch.sscname ?? "—")}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">{fmtMoney(ch.sscmoney)}</TableCell>
                            <TableCell className="font-mono text-xs">{String(ch.sscbillno ?? "—")}</TableCell>
                            <TableCell className="text-xs whitespace-nowrap">
                              {String(ch.sscflag_label ?? ch.sscflag ?? "—")}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </section>
            </div>
          )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
