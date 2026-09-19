import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export interface AuditUsageBreakdownItem {
  key: string;
  name: string;
  username?: string;
  login_count?: number;
  module_count?: number;
  usage_users?: number;
  enter_count?: number;
  query_count?: number;
  operation_count: number;
  last_used_at: string;
}

export function AuditUsageBreakdown({ dimension, items }: {
  dimension: "person" | "module";
  items: AuditUsageBreakdownItem[];
}) {
  const [keyword, setKeyword] = useState("");
  const isPerson = dimension === "person";
  const search = keyword.trim().toLocaleLowerCase();
  const filtered = items.filter((item) => [item.name, item.username, item.key]
    .some((value) => value?.toLocaleLowerCase().includes(search)));
  const total = items.reduce((sum, item) => sum + item.operation_count, 0);
  const max = Math.max(1, ...items.map((item) => item.operation_count));
  const number = (value?: number) => (value ?? 0).toLocaleString("zh-CN");
  return (
    <div className="mt-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-500">共 {number(items.length)} {isPerson ? "个账号（含未关联记录分组）" : "个模块"}，操作 {number(total)} 次 · 按操作次数降序</p>
        <Input aria-label={isPerson ? "搜索统计人员" : "搜索统计模块"}
          placeholder={isPerson ? "搜索姓名、账号" : "搜索模块名称、编码"}
          className="w-full sm:w-60" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
      </div>
      <div className="max-h-[440px] overflow-auto rounded-lg border border-slate-200">
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-white">
            <TableRow>
              <TableHead>{isPerson ? "姓名 / 账号" : "使用模块"}</TableHead>
              <TableHead className="text-right whitespace-nowrap">{isPerson ? "成功登录次数" : "使用人数"}</TableHead>
              <TableHead className="text-right whitespace-nowrap">{isPerson ? "使用模块数" : "进入次数"}</TableHead>
              {!isPerson && <TableHead className="text-right whitespace-nowrap">查询次数</TableHead>}
              <TableHead className="text-right whitespace-nowrap">操作次数</TableHead>
              <TableHead className="text-right whitespace-nowrap">操作占比</TableHead>
              <TableHead className="whitespace-nowrap">最近使用时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((item) => (
              <TableRow key={item.key}>
                <TableCell className="min-w-40">
                  <div className="font-medium">{item.name}</div>
                  <div className="text-xs text-slate-500">{isPerson ? item.username : item.key}</div>
                </TableCell>
                <TableCell className="text-right tabular-nums">{number(isPerson ? item.login_count : item.usage_users)}</TableCell>
                <TableCell className="text-right tabular-nums">{number(isPerson ? item.module_count : item.enter_count)}</TableCell>
                {!isPerson && <TableCell className="text-right tabular-nums">{number(item.query_count)}</TableCell>}
                <TableCell className="min-w-32 text-right tabular-nums">
                  {number(item.operation_count)}
                  <div className="mt-1 h-1 rounded bg-blue-50"><div className="h-1 rounded bg-blue-400" style={{ width: `${item.operation_count / max * 100}%` }} /></div>
                </TableCell>
                <TableCell className="text-right tabular-nums">{total ? (item.operation_count / total * 100).toFixed(1) : "0.0"}%</TableCell>
                <TableCell className="whitespace-nowrap">{new Date(item.last_used_at).toLocaleString("zh-CN", { hour12: false })}</TableCell>
              </TableRow>
            ))}
            {!filtered.length && <TableRow><TableCell colSpan={isPerson ? 6 : 7} className="h-32 text-center text-slate-500">
              {search ? "没有匹配的统计记录" : "所选周期暂无使用记录"}
            </TableCell></TableRow>}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
