import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import {
  DEPARTMENT_SCOPE_ALL_LABEL,
  DEPARTMENT_SCOPE_ALL_VALUE,
  POINTS_ACTIVITY_START_DATE,
  clampPointsActivityEndDate,
  memberLevelLabel,
  memberLevelSearchKeyword,
  pointAnalysisQueryMessage,
  pointsActivityDefaultEndDate,
  pointStatusLabel,
  pointStatusTone,
  pointTicketTimeLabel,
  salesSharePercent,
} from "@/lib/points-activity-analysis";

type Row = Record<string, string | number | null>;

type DashboardResponse = {
  summary: Row;
  department_options: Row[];
  departments: Row[];
  groups: Row[];
  members: Row[];
  tickets: Row[];
};

const money = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value || 0));

const number = (value: unknown) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value || 0));

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") qs.set(key, String(value));
  });
  const text = qs.toString();
  return text ? `?${text}` : "";
}

function localDate() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function StatusBadge({ status }: { status?: string | null }) {
  const tone = pointStatusTone(status);
  return (
    <Badge variant={tone === "danger" ? "destructive" : "secondary"} className={tone === "success" ? "bg-emerald-100 text-emerald-800" : ""}>
      {pointStatusLabel(status)}
    </Badge>
  );
}

export default function PointsActivityAnalysisPage() {
  const [startDate, setStartDate] = useState(POINTS_ACTIVITY_START_DATE);
  const [endDate, setEndDate] = useState(() => pointsActivityDefaultEndDate(localDate()));
  const [departmentName, setDepartmentName] = useState(DEPARTMENT_SCOPE_ALL_VALUE);
  const [groupCode, setGroupCode] = useState("");
  const [memberNo, setMemberNo] = useState("");
  const [keyword, setKeyword] = useState("");
  const [drillMode, setDrillMode] = useState<"departments" | "groups">("departments");
  const [drillDepartmentName, setDrillDepartmentName] = useState("");

  const resetDrill = () => {
    setDrillMode("departments");
    setDrillDepartmentName("");
  };

  const changeDepartmentFilter = (value: string) => {
    setDepartmentName(value);
    setGroupCode("");
    resetDrill();
  };

  const changeStartDate = (value: string) => {
    setStartDate(value);
    setEndDate((currentEndDate) => clampPointsActivityEndDate(value, currentEndDate));
    resetDrill();
  };

  const changeEndDate = (value: string) => {
    setEndDate(clampPointsActivityEndDate(startDate, value));
    resetDrill();
  };

  const common = useMemo(
    () => ({
      start_date: startDate,
      end_date: endDate,
      department_name: departmentName === DEPARTMENT_SCOPE_ALL_VALUE ? "" : departmentName,
      group_code: groupCode,
    }),
    [startDate, endDate, departmentName, groupCode],
  );

  const dashboard = useQuery<DashboardResponse>({
    queryKey: ["/api/activity-analysis/points/dashboard", common, keyword, memberNo],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/points/dashboard${buildQuery({ ...common, keyword: memberLevelSearchKeyword(keyword), member_no: memberNo, limit: 200 })}`,
      ),
  });

  useEffect(() => {
    const options = dashboard.data?.department_options;
    if (!options) return;
    if (!options.length) {
      if (departmentName !== DEPARTMENT_SCOPE_ALL_VALUE) setDepartmentName(DEPARTMENT_SCOPE_ALL_VALUE);
      return;
    }
    const optionNames = new Set(options.map((option) => String(option.department_name || "")));
    if (departmentName !== DEPARTMENT_SCOPE_ALL_VALUE && !optionNames.has(departmentName)) {
      setDepartmentName(DEPARTMENT_SCOPE_ALL_VALUE);
    }
  }, [departmentName, dashboard.data?.department_options]);

  const summary = dashboard.data?.summary || {};
  const queryMessage = pointAnalysisQueryMessage(dashboard);
  const isPageLoading = dashboard.isLoading || dashboard.isFetching;
  const summaryMoney = (value: unknown) => (isPageLoading ? "加载中" : money(value));
  const summaryNumber = (value: unknown) => (isPageLoading ? "加载中" : number(value));
  const totalSalesAmount = Number(summary.level_total_sales_amount || 0);
  const totalPersonCount = Number(summary.level_total_person_count || 0);
  const salesSummaryItems = [
    { label: "黑钻会员销售", value: summary.black_diamond_sales_amount, count: summary.black_diamond_person_count },
    { label: "黑金会员销售", value: summary.black_gold_sales_amount, count: summary.black_gold_person_count },
    { label: "金星会员销售", value: summary.gold_star_sales_amount, count: summary.gold_star_person_count },
    { label: "银星会员销售", value: summary.silver_star_sales_amount, count: summary.silver_star_person_count },
    { label: "非会员销售", value: summary.non_member_sales_amount, count: summary.non_member_person_count },
  ];
  const refresh = () => dashboard.refetch();

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">中心年中庆活动</h1>
          <p className="mt-1 text-sm text-muted-foreground">仅核对购物中心黑金、黑钻会员多倍积分，缺规则、积分率为0、付款分摊不平时标记待复核。</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-5">
          <div>
            <Label>开始日期</Label>
            <Input type="date" min={POINTS_ACTIVITY_START_DATE} value={startDate} onChange={(event) => changeStartDate(event.target.value)} />
          </div>
          <div>
            <Label>结束日期</Label>
            <Input type="date" min={POINTS_ACTIVITY_START_DATE} value={endDate} onChange={(event) => changeEndDate(event.target.value)} />
          </div>
          <div>
            <Label>部门名称</Label>
            <Select value={departmentName} onValueChange={changeDepartmentFilter}>
              <SelectTrigger className="mt-1 w-full">
                <SelectValue placeholder="请选择部门" />
              </SelectTrigger>
              <SelectContent className="z-50 bg-white border shadow-xl">
                <SelectItem value={DEPARTMENT_SCOPE_ALL_VALUE}>{DEPARTMENT_SCOPE_ALL_LABEL}</SelectItem>
                {(dashboard.data?.department_options || []).map((option) => {
                  const value = String(option.department_name || "");
                  if (!value) return null;
                  return (
                    <SelectItem key={`${option.department_code || ""}-${value}`} value={value}>
                      {value}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>柜组编码</Label>
            <Input value={groupCode} onChange={(event) => { setGroupCode(event.target.value); resetDrill(); }} placeholder="可选" />
          </div>
          <Button className="self-end" variant="outline" onClick={refresh}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
        </div>
      </div>

      {queryMessage ? (
        <Card>
          <CardContent className="p-4 text-sm text-muted-foreground">{queryMessage}</CardContent>
        </Card>
      ) : null}

      {!dashboard.isError ? (
        <>
      <div className="overflow-x-auto rounded-md border border-slate-300 bg-white">
        <div className="flex min-w-[1120px] items-stretch divide-x divide-slate-200">
          <div className="flex min-w-[220px] flex-col justify-center px-5 py-4">
            <p className="text-sm font-medium text-muted-foreground">总销售额</p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-950">{summaryMoney(summary.level_total_sales_amount)}</p>
            <p className="mt-1 text-xs font-medium text-slate-500">总人数 {summaryNumber(summary.level_total_person_count)}</p>
          </div>
          {salesSummaryItems.map((item) => (
            <div key={item.label} className="flex min-w-[178px] flex-1 flex-col justify-center px-5 py-4">
              <p className="text-sm font-medium text-muted-foreground">{item.label}</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-950">{summaryMoney(item.value)}</p>
              <p className="mt-1 text-xs font-medium text-slate-500">占比 {isPageLoading ? "加载中" : salesSharePercent(item.value, totalSalesAmount)}</p>
              <p className="mt-1 text-xs font-medium text-slate-500">
                人数 {summaryNumber(item.count)} · 人数占比 {isPageLoading ? "加载中" : salesSharePercent(item.count, totalPersonCount)}
              </p>
            </div>
          ))}
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>{drillMode === "departments" ? "部门汇总" : `${drillDepartmentName || "未归属部门"} / 柜组汇总`}</CardTitle>
          {drillMode === "groups" ? (
            <Button variant="outline" size="sm" onClick={() => { setGroupCode(""); resetDrill(); }}>
              返回部门汇总
            </Button>
          ) : null}
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {drillMode === "departments" ? (
            <Table>
              <TableHeader><TableRow><TableHead>部门</TableHead><TableHead className="text-right">黑钻人数</TableHead><TableHead className="text-right">黑金人数</TableHead><TableHead className="text-right">销售额</TableHead><TableHead className="text-right">积分基数</TableHead><TableHead className="text-right">实际积分发放数</TableHead><TableHead className="text-right">差异</TableHead><TableHead className="text-right">待复核</TableHead></TableRow></TableHeader>
              <TableBody>
                <TableRow className="bg-slate-50 font-semibold">
                  <TableCell>合计</TableCell>
                  <TableCell className="text-right">{summaryNumber(summary.black_diamond_member_count)}</TableCell>
                  <TableCell className="text-right">{summaryNumber(summary.black_gold_member_count)}</TableCell>
                  <TableCell className="text-right">{summaryMoney(summary.total_sales_amount)}</TableCell>
                  <TableCell className="text-right">{summaryMoney(summary.point_basis_amount)}</TableCell>
                  <TableCell className="text-right">{summaryNumber(summary.actual_point)}</TableCell>
                  <TableCell className="text-right">{summaryNumber(summary.point_diff)}</TableCell>
                  <TableCell className="text-right">{summaryNumber(summary.issue_count)}</TableCell>
                </TableRow>
                {(dashboard.data?.departments || []).map((row, index) => (
                <TableRow
                  key={index}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => {
                    setDrillDepartmentName(String(row.department_name || ""));
                    setDrillMode("groups");
                    setGroupCode("");
                    setMemberNo("");
                  }}
                >
                  <TableCell>{row.department_name || row.department_code || "未归属"}</TableCell>
                  <TableCell className="text-right">{number(row.black_diamond_member_count)}</TableCell>
                  <TableCell className="text-right">{number(row.black_gold_member_count)}</TableCell>
                  <TableCell className="text-right">{money(row.total_sales_amount)}</TableCell>
                  <TableCell className="text-right">{money(row.point_basis_amount)}</TableCell>
                  <TableCell className="text-right">{number(row.actual_point)}</TableCell>
                  <TableCell className="text-right">{number(row.point_diff)}</TableCell>
                  <TableCell className="text-right">{number(row.issue_count)}</TableCell>
                </TableRow>
              ))}
              {!(dashboard.data?.departments || []).length ? (
                <TableRow><TableCell colSpan={8} className="py-6 text-center text-muted-foreground">暂无部门汇总</TableCell></TableRow>
              ) : null}
              </TableBody>
            </Table>
          ) : (
            <Table>
              <TableHeader><TableRow><TableHead>柜组</TableHead><TableHead className="text-right">黑钻人数</TableHead><TableHead className="text-right">黑金人数</TableHead><TableHead className="text-right">销售额</TableHead><TableHead className="text-right">积分基数</TableHead><TableHead className="text-right">实际积分发放数</TableHead><TableHead className="text-right">差异</TableHead><TableHead className="text-right">待复核</TableHead></TableRow></TableHeader>
              <TableBody>{(dashboard.data?.groups || []).filter((row) => String(row.department_name || "") === drillDepartmentName).map((row, index) => (
                <TableRow
                  key={`${row.group_code || ""}-${index}`}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => {
                    setGroupCode(String(row.group_code || ""));
                    setMemberNo("");
                  }}
                >
                  <TableCell>{row.group_name || row.group_code || "未归属"}</TableCell>
                  <TableCell className="text-right">{number(row.black_diamond_member_count)}</TableCell>
                  <TableCell className="text-right">{number(row.black_gold_member_count)}</TableCell>
                  <TableCell className="text-right">{money(row.total_sales_amount)}</TableCell>
                  <TableCell className="text-right">{money(row.point_basis_amount)}</TableCell>
                  <TableCell className="text-right">{number(row.actual_point)}</TableCell>
                  <TableCell className="text-right">{number(row.point_diff)}</TableCell>
                  <TableCell className="text-right">{number(row.issue_count)}</TableCell>
                </TableRow>
              ))}
              {!(dashboard.data?.groups || []).some((row) => String(row.department_name || "") === drillDepartmentName) ? (
                <TableRow><TableCell colSpan={8} className="py-6 text-center text-muted-foreground">暂无柜组汇总</TableCell></TableRow>
              ) : null}</TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>部门销售会员</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <div className="mb-3 flex gap-2">
              <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="会员号、黑金或黑钻" />
              <Button variant="outline"><Search className="h-4 w-4" /></Button>
            </div>
            <Table>
              <TableHeader><TableRow><TableHead>会员</TableHead><TableHead>等级</TableHead><TableHead className="text-right">销售额</TableHead><TableHead className="text-right">实际积分</TableHead><TableHead className="text-right">差异</TableHead><TableHead className="text-right">待复核</TableHead></TableRow></TableHeader>
              <TableBody>{(dashboard.data?.members || []).map((row, index) => (
                <TableRow key={index} className="cursor-pointer hover:bg-slate-50" onClick={() => setMemberNo(String(row.member_no || ""))}>
                  <TableCell>{row.member_no || "未刷卡"}</TableCell>
                  <TableCell>{memberLevelLabel(row.customer_level)}</TableCell>
                  <TableCell className="text-right">{money(row.total_sales_amount)}</TableCell>
                  <TableCell className="text-right">{number(row.actual_point)}</TableCell>
                  <TableCell className="text-right">{number(row.point_diff)}</TableCell>
                  <TableCell className="text-right">{number(row.issue_count)}</TableCell>
                </TableRow>
              ))}</TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>小票 / 积分明细</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <div className="mb-3 flex gap-2">
              <Input value={memberNo} onChange={(event) => setMemberNo(event.target.value)} placeholder="会员号筛选" />
              <Button variant="outline"><Search className="h-4 w-4" /></Button>
            </div>
            <Table>
              <TableHeader><TableRow><TableHead>小票号</TableHead><TableHead>时间</TableHead><TableHead>会员</TableHead><TableHead className="text-right">销售额</TableHead><TableHead className="text-right">积分基数</TableHead><TableHead className="text-right">实际/应送</TableHead><TableHead>状态</TableHead></TableRow></TableHeader>
              <TableBody>{(dashboard.data?.tickets || []).map((row, index) => (
                <TableRow key={index}>
                  <TableCell>{row.billno}</TableCell>
                  <TableCell>{pointTicketTimeLabel(String(row.sale_time || ""))}</TableCell>
                  <TableCell>{row.member_no}</TableCell>
                  <TableCell className="text-right">{money(row.total_sales_amount)}</TableCell>
                  <TableCell className="text-right">{money(row.point_basis_amount)}</TableCell>
                  <TableCell className="text-right">{number(row.actual_point)} / {number(row.expected_point)}</TableCell>
                  <TableCell><StatusBadge status={String(row.status || "")} /></TableCell>
                </TableRow>
              ))}</TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
        </>
      ) : null}
    </div>
  );
}
