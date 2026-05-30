import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

export interface ContractUnitInfo {
  id: number;
  floor_id: number;
  unit_code: string;
  status: string;
  manual_area?: number | null;
  store_code?: string | null;
  building_code?: string | null;
  floor_code?: string | null;
  floor_name?: string | null;
}

export interface ErpContractItem {
  cmfcontno: string;
  cmfmfid: string;
  cmfmarket?: string | null;
  cmfeffdate?: string | null;
  cmflapdate?: string | null;
  cmfjzmj?: number | null;
  cmfsymj?: number | null;
  cmfavgsyf?: number | null;
  cmftotsyf?: number | null;
  cmfcharter?: number | null;
  cmfmemo?: string | null;
  cmfbrand?: string | null;
  cmfaddr?: string | null;
  cmfarea?: string | null;
  cmfismaster?: string | null;
  cmfzjmj?: number | null;
  cmcontno?: string | null;
  cmstatus?: string | null;
  cmtype?: string | null;
  contract_type_name?: string | null;
  cmmfid?: string | null;
  cmsupid?: string | null;
  supplier_name?: string | null;
  cmwmid?: string | null;
  cmtitle?: string | null;
  cmobject?: string | null;
  cmppname?: string | null;
  cmcatname?: string | null;
  cmeffdate?: string | null;
  cmlapdate?: string | null;
  cmmoney?: number | null;
  cmpaycode?: string | null;
  cmbysettle?: string | null;
  cmyfkmode?: string | null;
  cmsetmode?: string | null;
  cmjsmkt?: string | null;
  cmkl?: number | null;
  cminputor?: string | null;
  cminputdate?: string | null;
  cmauditor?: string | null;
  cmauditdate?: string | null;
  cmannulor?: string | null;
  cmannuldate?: string | null;
  cmmemo?: string | null;
  cmmasterno?: string | null;
  cmseqno?: string | null;
  cmcontact?: string | null;
  cmadd?: string | null;
  cmtel?: string | null;
  cmfax?: string | null;
  cmemail?: string | null;
  cmchar9?: string | null;
  cmsptype?: string | null;
  signdate?: string | null;
  deliverydate?: string | null;
  tackbackdate?: string | null;
  sjcgdate?: string | null;
  effectdate?: string | null;
  zxqsrq?: string | null;
  zxjzrq?: string | null;
  is_current_effective: boolean;
  status_label: string;
}

export interface UnitContractsResponse {
  unit: ContractUnitInfo;
  active_contract?: ErpContractItem | null;
  active_contract_count: number;
  contracts: ErpContractItem[];
}

export interface ContractListItem {
  cmcontno: string;
  cmstatus?: string | null;
  status_label?: string | null;
  cmtype?: string | null;
  contract_type_name?: string | null;
  cmsupid?: string | null;
  supplier_name?: string | null;
  cmwmid?: string | null;
  cmtitle?: string | null;
  cmobject?: string | null;
  cmppname?: string | null;
  cmcatname?: string | null;
  cmeffdate?: string | null;
  cmlapdate?: string | null;
  cmmoney?: number | null;
  cmpaycode?: string | null;
  cmyfkmode?: string | null;
  cmsetmode?: string | null;
  cmjsmkt?: string | null;
  cminputor?: string | null;
  cminputdate?: string | null;
  cmauditor?: string | null;
  cmauditdate?: string | null;
  cmchar9?: string | null;
  group_codes?: string | null;
  group_names?: string | null;
  range_brands?: string | null;
  range_start_date?: string | null;
  range_end_date?: string | null;
  contract_area?: number | null;
  is_clear?: boolean | null;
  clear_flags?: string | null;
  bottom_amount?: number | null;
  bottom_profit?: number | null;
}

export interface ContractListResponse {
  items: ContractListItem[];
  count: number;
  skip: number;
  limit: number;
}

export interface ContractMainDetail {
  cmcontno: string;
  cmstatus?: string | null;
  status_label?: string | null;
  cmtype?: string | null;
  contract_type_name?: string | null;
  cmmfid?: string | null;
  cmsupid?: string | null;
  supplier_name?: string | null;
  cmwmid?: string | null;
  cmtitle?: string | null;
  cmobject?: string | null;
  cmppname?: string | null;
  cmcatname?: string | null;
  cmeffdate?: string | null;
  cmlapdate?: string | null;
  cmmoney?: number | null;
  cmpaycode?: string | null;
  cmbysettle?: string | null;
  cmyfkmode?: string | null;
  cmsetmode?: string | null;
  cmjsmkt?: string | null;
  cmchar9?: string | null;
  cmsptype?: string | null;
  signdate?: string | null;
  deliverydate?: string | null;
  tackbackdate?: string | null;
  sjcgdate?: string | null;
  effectdate?: string | null;
  zxqsrq?: string | null;
  zxjzrq?: string | null;
  cmcontact?: string | null;
  cmadd?: string | null;
  cmtel?: string | null;
  cmemail?: string | null;
  cmmemo?: string | null;
  cmmasterno?: string | null;
  cmseqno?: string | null;
}

export interface ContractManaframeDetail {
  cmfcontno: string;
  cmfmfid?: string | null;
  group_name?: string | null;
  cmfmarket?: string | null;
  cmfeffdate?: string | null;
  cmflapdate?: string | null;
  cmfjzmj?: number | null;
  cmfsymj?: number | null;
  cmfzjmj?: number | null;
  cmfavgsyf?: number | null;
  cmftotsyf?: number | null;
  cmfcharter?: number | null;
  cmfnum1?: number | null;
  cmfnum2?: number | null;
  cmfnum3?: number | null;
  cmfnum4?: number | null;
  cmfnum5?: number | null;
  cmfbrand?: string | null;
  cmfaddr?: string | null;
  cmfarea?: string | null;
  cmfismaster?: string | null;
  cmfmemo?: string | null;
}

export interface ContractBdDetail {
  cbcontno: string;
  cbseqno: number;
  cbmkt?: string | null;
  cbmfid?: string | null;
  group_name?: string | null;
  cbeffdate?: string | null;
  cblapdate?: string | null;
  cbisrunbd?: string | null;
  cbisrunqs?: string | null;
  cbsum?: number | null;
  cbrate?: number | null;
  cbsum1?: number | null;
  cbrate1?: number | null;
  cbsum2?: number | null;
  cbrate2?: number | null;
  cbsum3?: number | null;
  cbrate3?: number | null;
  cbsum4?: number | null;
  cbrate4?: number | null;
  cbsum5?: number | null;
  cbrate5?: number | null;
  cbsum6?: number | null;
  cbrate6?: number | null;
  cbprofit?: number | null;
  cbsettype?: string | null;
  cbrentunit?: string | null;
  cbmanaunit?: string | null;
  cbpopunit?: string | null;
  cbrentprice?: number | null;
  cbnamaprice?: number | null;
  cbpopprice?: number | null;
  cbiscalcrent?: string | null;
  cbsalekh?: number | null;
  cbsalerate?: number | null;
  /** 保底区间完成销售收入，来自 contbd_xs.xssr（ETL 汇总） */
  xssr?: number | null;
}

export interface ContractCyclistDetail {
  cclcontno: string;
  cclseqno: number;
  cclmkt?: string | null;
  cclmfid?: string | null;
  group_name?: string | null;
  ccleffdate?: string | null;
  ccllapdate?: string | null;
  cclitemid?: string | null;
  cclitemunit?: string | null;
  cclitemprice?: number | null;
  cclsumamount?: number | null;
  cclystype?: number | null;
  cclysnum?: number | null;
  cclisfree?: string | null;
  cclflag?: string | null;
  cclpchflag?: string | null;
}

export interface ContractSupchargeDetail {
  csccontno: string;
  cscrowno: number;
  cscispub?: string | null;
  cscmfid?: string | null;
  group_name?: string | null;
  cscmarket?: string | null;
  cscchargecode?: string | null;
  cscchargename?: string | null;
  csceffdate?: string | null;
  csclapdate?: string | null;
  cscsetmon?: string | null;
  cscismcjs?: string | null;
  cscvalue?: number | null;
  csctotal?: number | null;
  cscisdeduct?: string | null;
  cscflag?: string | null;
  cscjsbillno?: string | null;
  cscmemo?: string | null;
  cscnum1?: number | null;
  cscnum2?: number | null;
  cscnum3?: number | null;
  cscisret?: string | null;
  cscretdate?: string | null;
  cscbottomvalues?: number | null;
  cscpeakvalues?: number | null;
}

export interface ContractDetailResponse {
  contract_no: string;
  contmain?: ContractMainDetail | null;
  contmanaframe: ContractManaframeDetail[];
  contbd: ContractBdDetail[];
  contcyclist: ContractCyclistDetail[];
  contsupcharge: ContractSupchargeDetail[];
  counts: {
    contmanaframe: number;
    contbd: number;
    contcyclist: number;
    contsupcharge: number;
  };
}

export function useUnitContracts(unitId?: number) {
  return useQuery({
    queryKey: ["unit-contracts", unitId ?? "none"],
    enabled: typeof unitId === "number" && Number.isFinite(unitId),
    queryFn: () => apiGet<UnitContractsResponse>(`/api/contracts/by-unit/${unitId}`),
  });
}

export function useContractsList(params?: {
  keyword?: string;
  status?: string;
  groupCode?: string;
  supplierCode?: string;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["contracts-list", params ?? {}],
    queryFn: () => {
      const searchParams = new URLSearchParams();
      const keyword = params?.keyword?.trim();
      const status = params?.status?.trim();
      const groupCode = params?.groupCode?.trim();
      const supplierCode = params?.supplierCode?.trim();
      if (keyword) searchParams.set("keyword", keyword);
      if (status && status !== "ALL") searchParams.set("status", status);
      if (groupCode) searchParams.set("group_code", groupCode);
      if (supplierCode) searchParams.set("supplier_code", supplierCode);
      searchParams.set("skip", String(params?.skip ?? 0));
      searchParams.set("limit", String(params?.limit ?? 100));
      return apiGet<ContractListResponse>(`/api/contracts/?${searchParams.toString()}`);
    },
  });
}

export function useContractDetail(contractNo?: string) {
  return useQuery({
    queryKey: ["contract-detail", contractNo ?? "none"],
    enabled: Boolean(contractNo?.trim()),
    queryFn: () => apiGet<ContractDetailResponse>(`/api/contracts/detail/${encodeURIComponent(contractNo!.trim())}`),
  });
}
