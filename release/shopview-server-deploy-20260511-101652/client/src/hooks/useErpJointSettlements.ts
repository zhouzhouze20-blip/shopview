import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

export type JointSettlementListItem = {
  sshbillno: string;
  /** suppayhead.sphmfid（经 paybatch / sshpayno 解析） */
  sphmfid?: string | null;
  /** sphmfid + manaframe.mfcname */
  sphmf_department_display?: string | null;
  /** paybatch.pbbillno，与 pbjsno=结算单号 关联，优先取 pbbilltype=J 的行 */
  pbbillno?: string | null;
  sshmkt: string | null;
  sshflag: string | null;
  sshpayflag: string | null;
  sshcontno: string | null;
  sshsupid: string | null;
  sshwmid: string | null;
  sshdate: string | null;
  sshlastdate: string | null;
  sshthisdate: string | null;
  sshenddate: string | null;
  inputor: string | null;
  auditor: string | null;
  auditdate: string | null;
  sshsjfkje: number | null;
  sshvc3: string | null;
  sshtotkk: number | null;
  sshsetje: number | null;
  sshinvno: string | null;
  sales_revenue_sum: number | null;
  fee_sum: number | null;
};

export type JointSettlementListResponse = {
  items: JointSettlementListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type JointSettlementDetailResponse = {
  head: Record<string, unknown>;
  /** ERP 表头（suppayhead 等），无数据时为 null */
  header_display: Record<string, unknown> | null;
  /** 按付款单号 sscpaybillno 的费用行 */
  charges_by_payment_bill: Record<string, unknown>[];
  paybatch: Record<string, unknown>[];
  /** paybatch × supsettledet（若库中有 supsettledet）；旧版后端可能无此字段 */
  paybatch_sales?: Record<string, unknown>[];
  lines: Record<string, unknown>[];
  charges: Record<string, unknown>[];
};

export type JointSettlementListParams = {
  page: number;
  page_size: number;
  mkt?: string;
  date_from?: string;
  date_to?: string;
  keyword?: string;
};

function buildQueryString(p: JointSettlementListParams): string {
  const q = new URLSearchParams();
  q.set("page", String(p.page));
  q.set("page_size", String(p.page_size));
  if (p.mkt?.trim()) q.set("mkt", p.mkt.trim());
  if (p.date_from) q.set("date_from", p.date_from);
  if (p.date_to) q.set("date_to", p.date_to);
  if (p.keyword?.trim()) q.set("keyword", p.keyword.trim());
  return q.toString();
}

export function useJointSettlementList(
  params: JointSettlementListParams,
  enabled = true,
) {
  const qs = buildQueryString(params);
  return useQuery({
    queryKey: ["/api/erp-settlements/joint-statements", qs],
    queryFn: () => apiGet<JointSettlementListResponse>(`/api/erp-settlements/joint-statements?${qs}`),
    enabled,
    staleTime: 30_000,
  });
}

export function useJointSettlementDetail(billNo: string | null) {
  return useQuery({
    queryKey: ["/api/erp-settlements/joint-statements/detail", billNo],
    queryFn: () =>
      apiGet<JointSettlementDetailResponse>(
        `/api/erp-settlements/joint-statements/${encodeURIComponent(billNo as string)}`,
      ),
    enabled: !!billNo && billNo.length > 0,
    staleTime: 60_000,
  });
}
