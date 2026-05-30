import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Activity, FileText, Plus, RefreshCw, Shield, Users, Building2, Filter, Search } from "lucide-react";

interface StoreOption {
  storeId: number;
  storeName: string;
}

interface PermissionItem {
  id: number;
  permission_code: string;
  permission_name: string;
  module_code: string;
  action_code: string;
}

const PERMISSION_MODULE_LABELS: Record<string, string> = {
  activity_analysis: "活动分析",
  base_map: "底图管理",
  business_unit: "经营单元",
  contract: "合同管理",
  counter: "柜位管理",
  dashboard: "经营概览",
  floor: "楼层管理",
  sales: "销售管理",
  settlement: "联营结算",
  supplier: "供应商管理",
  system: "系统管理",
  tenant: "商户管理",
  unit_map_version: "柜位图版本",
};

interface PostItem {
  id: number;
  post_code: string;
  post_name: string;
  level: number;
}

interface RoleItem {
  id: number;
  role_code: string;
  role_name: string;
  role_level: number;
  is_system: boolean;
  is_active: boolean;
  permission_ids: number[];
  permission_codes: string[];
}

interface DepartmentItem {
  id: number;
  store_id: number;
  store_name?: string;
  dept_code: string;
  dept_name: string;
  manager_user_id?: number | null;
  manager_name?: string | null;
  is_active: boolean;
}

interface UserAssignment {
  id?: number;
  store_id: number;
  store_name?: string;
  department_id: number;
  department_name?: string;
  post_id?: number | null;
  post_name?: string | null;
  is_primary: boolean;
}

interface UserItem {
  user_id: number;
  username: string;
  real_name?: string | null;
  email?: string | null;
  phone?: string | null;
  status: string;
  default_store_id?: number | null;
  employee_no?: string | null;
  is_active: boolean;
  role_ids: number[];
  role_codes: string[];
  role_names: string[];
  department_assignments: UserAssignment[];
}

interface MetaOption {
  id: number;
  name: string;
}

interface DataPolicyItem {
  id?: number;
  dimension_type: string;
  dimension_value: string;
  include_children: boolean;
}

interface DataPolicy {
  id: number;
  subject_type: string;
  subject_id: number;
  subject_name?: string | null;
  resource_code: string;
  action_code: string;
  scope_mode: string;
  effect: string;
  priority: number;
  is_active: boolean;
  source_type?: string | null;
  source_system?: string | null;
  external_scope_id?: string | null;
  external_scope_name?: string | null;
  synced_at?: string | null;
  items: DataPolicyItem[];
}

interface WeComRoleScopeRule {
  id: number;
  rule_name: string;
  corp_id?: string | null;
  priority: number;
  match_mode: "ALL" | "ANY";
  wecom_userids: string[];
  name_keywords: string[];
  department_keywords: string[];
  position_keywords: string[];
  role_codes: string[];
  scope_mode: "ALL" | "CUSTOM" | "NONE";
  scope_dimensions: Record<string, string[]>;
  is_active: boolean;
  remark?: string | null;
  created_at: string;
  updated_at?: string | null;
}

interface SystemMeta {
  subject_types: string[];
  resource_codes: string[];
  action_codes: string[];
  scope_modes: string[];
  effects: string[];
  dimension_types: string[];
  users: MetaOption[];
  roles: MetaOption[];
}

interface ContractPermissionOption {
  id: number;
  store_id?: number | null;
  code: string;
  name: string;
  department_code?: string | null;
  department_name?: string | null;
  brand_name?: string | null;
}

/** 与后端 manaframe 关联门店一行一条，用于业务范围配置（与合同/销售数据口径一致） */
interface ContractScopeMatrixRow {
  store_id: number;
  store_code: string;
  store_name: string;
  department_code: string;
  department_name: string;
  group_id: number;
  group_code: string;
  group_name: string;
}

interface ContractPermissionOptions {
  stores: ContractPermissionOption[];
  /** 已废弃：手工 departments 表与柜组部门不一致，勿再使用 */
  departments: ContractPermissionOption[];
  groups: ContractPermissionOption[];
  scope_matrix: ContractScopeMatrixRow[];
}

interface ContractPermissionUser {
  user_id: number;
  username: string;
  real_name?: string | null;
  employee_no?: string | null;
  status: string;
  is_active: boolean;
  role_names: string[];
  has_contract_view: boolean;
  /** 本页「开通」状态：合同查看人员角色或手工业务范围（勿与 has_contract_view 混用） */
  scope_tab_active?: boolean;
  manual_scope_mode?: "ALL" | "CUSTOM";
  manual_store_values?: string[];
  manual_department_values?: string[];
  manual_group_values?: string[];
  scope_mode: "ALL" | "CUSTOM";
  store_values: string[];
  department_values: string[];
  group_values: string[];
  manual_scope_count: number;
  erp_scope_count: number;
}

type SystemConfigTab = "users" | "roles" | "departments" | "contract-permissions" | "wecom-rules" | "policies" | "audit-logs";

interface SystemConfigPageProps {
  initialTab?: SystemConfigTab;
}

interface PagedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

interface LoginLogItem {
  id: number;
  user_id?: number | null;
  username?: string | null;
  real_name?: string | null;
  identity_type?: string | null;
  identifier?: string | null;
  login_result: "SUCCESS" | "FAILED" | string;
  ip_address?: string | null;
  user_agent?: string | null;
  device_type?: "MOBILE" | "DESKTOP" | "UNKNOWN" | string | null;
  created_at: string;
}

interface OperationLogItem {
  id: number;
  user_id?: number | null;
  username?: string | null;
  real_name?: string | null;
  action_code: string;
  resource_code: string;
  target_id?: string | null;
  detail?: Record<string, unknown> | null;
  ip_address?: string | null;
  created_at: string;
}

const loginDeviceLabel: Record<string, string> = {
  MOBILE: "手机端",
  DESKTOP: "电脑端",
  UNKNOWN: "未知",
};

const emptyUserForm = {
  username: "",
  real_name: "",
  email: "",
  phone: "",
  status: "ACTIVE",
  default_store_id: "",
  employee_no: "",
  is_active: true,
  password: "",
  role_ids: [] as number[],
  department_assignments: [] as Array<{
    store_id: string;
    department_id: string;
    post_id: string;
    is_primary: boolean;
  }>,
};

const emptyRoleForm = {
  role_code: "",
  role_name: "",
  role_level: "0",
  is_system: true,
  is_active: true,
  permission_ids: [] as number[],
};

const emptyDepartmentForm = {
  store_id: "",
  dept_code: "",
  dept_name: "",
  manager_user_id: "",
  is_active: true,
};

const emptyPolicyForm = {
  subject_type: "ROLE",
  subject_id: "",
  resource_code: "business_scope",
  action_code: "view",
  scope_mode: "CUSTOM",
  effect: "ALLOW",
  priority: "100",
  is_active: true,
  source_type: "MANUAL",
  source_system: "shopview",
  external_scope_id: "",
  external_scope_name: "",
  store_values: "",
  department_values: "",
  group_values: "",
  floor_values: "",
  unit_values: "",
  supplier_values: "",
  brand_values: "",
  category_values: "",
};

const emptyContractPermissionForm = {
  enabled: true,
  scope_mode: "CUSTOM" as "ALL" | "CUSTOM",
  filter_store_values: [] as string[],
  store_values: [] as string[],
  department_values: [] as string[],
  group_values: [] as string[],
};

const emptyWeComRuleForm = {
  rule_name: "",
  corp_id: "",
  priority: "100",
  match_mode: "ALL" as "ALL" | "ANY",
  wecom_userids: "",
  name_keywords: "",
  department_keywords: "",
  position_keywords: "",
  role_codes: [] as string[],
  scope_mode: "CUSTOM" as "ALL" | "CUSTOM" | "NONE",
  scope_dimensions: '{\n  "department": ["$department"]\n}',
  is_active: true,
  remark: "",
};

const splitValues = (value: string) =>
  value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);

const joinValues = (values?: string[]) => (values ?? []).join("\n");

const parseScopeDimensions = (value: string): Record<string, string[]> => {
  const text = value.trim();
  if (!text) return {};
  const parsed = JSON.parse(text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("数据范围 JSON 必须是对象");
  }
  const out: Record<string, string[]> = {};
  Object.entries(parsed).forEach(([key, raw]) => {
    if (!Array.isArray(raw)) {
      throw new Error(`${key} 的值必须是数组`);
    }
    out[key] = raw.map((item) => String(item).trim()).filter(Boolean);
  });
  return out;
};

const buildQueryString = (params: Record<string, string | number | undefined | null>) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    searchParams.set(key, String(value));
  });
  const query = searchParams.toString();
  return query ? `?${query}` : "";
};

const formatDateTime = (value?: string | null) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
};

/** 与后端 scope 匹配一致（authz._norm），用于勾选状态比较 */
const normScopeCode = (value: string) => String(value ?? "").trim().toUpperCase();

/** 门店主键统一成数字字符串，避免 1 / "1" / "01" 与筛选门店勾选不一致 */
const normStoreIdForScope = (value: unknown): string => {
  if (value == null || value === "") return "";
  const s = String(value).trim();
  const n = Number(s);
  if (Number.isFinite(n)) return String(Math.trunc(n));
  return normScopeCode(s);
};

const uniqueByNorm = (values: string[], normalizer: (value: string) => string = normScopeCode): string[] => {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const value of values) {
    const key = normalizer(value);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(value);
  }
  return out;
};

const buildPolicyItems = (form: typeof emptyPolicyForm): DataPolicyItem[] => {
  const groups: Array<[string, string[]]> = [
    ["store", splitValues(form.store_values)],
    ["department", splitValues(form.department_values)],
    ["group", splitValues(form.group_values)],
    ["floor", splitValues(form.floor_values)],
    ["unit", splitValues(form.unit_values)],
    ["supplier", splitValues(form.supplier_values)],
    ["brand", splitValues(form.brand_values)],
    ["category", splitValues(form.category_values)],
  ];
  return groups.flatMap(([dimensionType, values]) =>
    values.map((value) => ({
      dimension_type: dimensionType,
      dimension_value: value,
      include_children: false,
    })),
  );
};

export default function SystemConfigPage({ initialTab = "users" }: SystemConfigPageProps) {
  const [tab, setTab] = useState<SystemConfigTab>(initialTab);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [departmentDialogOpen, setDepartmentDialogOpen] = useState(false);
  const [policyDialogOpen, setPolicyDialogOpen] = useState(false);
  const [contractPermissionDialogOpen, setContractPermissionDialogOpen] = useState(false);
  const [wecomRuleDialogOpen, setWecomRuleDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [editingRole, setEditingRole] = useState<RoleItem | null>(null);
  const [editingDepartment, setEditingDepartment] = useState<DepartmentItem | null>(null);
  const [editingPolicy, setEditingPolicy] = useState<DataPolicy | null>(null);
  const [editingContractPermission, setEditingContractPermission] = useState<ContractPermissionUser | null>(null);
  const [editingWeComRule, setEditingWeComRule] = useState<WeComRoleScopeRule | null>(null);
  const [userForm, setUserForm] = useState(emptyUserForm);
  const [roleForm, setRoleForm] = useState(emptyRoleForm);
  const [departmentForm, setDepartmentForm] = useState(emptyDepartmentForm);
  const [policyForm, setPolicyForm] = useState(emptyPolicyForm);
  const [contractPermissionForm, setContractPermissionForm] = useState(emptyContractPermissionForm);
  const [wecomRuleForm, setWecomRuleForm] = useState(emptyWeComRuleForm);
  const [userSearchText, setUserSearchText] = useState("");
  const [auditLogType, setAuditLogType] = useState<"login" | "operation">("login");
  const [auditKeyword, setAuditKeyword] = useState("");
  const [auditStartDate, setAuditStartDate] = useState("");
  const [auditEndDate, setAuditEndDate] = useState("");
  const [loginResultFilter, setLoginResultFilter] = useState("ALL");
  const [operationResourceFilter, setOperationResourceFilter] = useState("ALL");
  const [operationActionFilter, setOperationActionFilter] = useState("ALL");
  const [activeScopeDepartmentKey, setActiveScopeDepartmentKey] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const { toast } = useToast();

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab]);

  const { data: stores = [] } = useQuery<StoreOption[]>({
    queryKey: ["/api/stores", { is_active: true }],
    queryFn: async () => {
      const data = await apiGet<any[]>("/api/stores?is_active=true");
      return data.map((store) => ({
        storeId: store.store_id ?? store.storeId,
        storeName: store.store_name ?? store.storeName,
      }));
    },
  });

  const { data: permissions = [] } = useQuery<PermissionItem[]>({
    queryKey: ["/api/system/permissions"],
    queryFn: () => apiGet<PermissionItem[]>("/api/system/permissions"),
  });

  const { data: posts = [] } = useQuery<PostItem[]>({
    queryKey: ["/api/system/posts"],
    queryFn: () => apiGet<PostItem[]>("/api/system/posts"),
  });

  const { data: roles = [] } = useQuery<RoleItem[]>({
    queryKey: ["/api/system/roles"],
    queryFn: () => apiGet<RoleItem[]>("/api/system/roles"),
  });

  const { data: departments = [] } = useQuery<DepartmentItem[]>({
    queryKey: ["/api/system/departments"],
    queryFn: () => apiGet<DepartmentItem[]>("/api/system/departments"),
  });

  const { data: users = [] } = useQuery<UserItem[]>({
    queryKey: ["/api/system/users"],
    queryFn: () => apiGet<UserItem[]>("/api/system/users"),
  });

  const { data: policies = [] } = useQuery<DataPolicy[]>({
    queryKey: ["/api/system/data-policies"],
    queryFn: () => apiGet<DataPolicy[]>("/api/system/data-policies"),
  });

  const { data: wecomRules = [] } = useQuery<WeComRoleScopeRule[]>({
    queryKey: ["/api/system/wecom-role-scope-rules"],
    queryFn: () => apiGet<WeComRoleScopeRule[]>("/api/system/wecom-role-scope-rules"),
  });

  const { data: meta } = useQuery<SystemMeta>({
    queryKey: ["/api/system/meta"],
    queryFn: () => apiGet<SystemMeta>("/api/system/meta"),
  });

  const { data: contractPermissionOptions = { stores: [], departments: [], groups: [], scope_matrix: [] } } = useQuery<ContractPermissionOptions>({
    queryKey: ["/api/system/contract-permissions/options"],
    queryFn: () => apiGet<ContractPermissionOptions>("/api/system/contract-permissions/options"),
  });

  const { data: contractPermissions = [] } = useQuery<ContractPermissionUser[]>({
    queryKey: ["/api/system/contract-permissions"],
    queryFn: () => apiGet<ContractPermissionUser[]>("/api/system/contract-permissions"),
  });

  const loginLogsQueryString = buildQueryString({
    keyword: auditKeyword.trim(),
    login_result: loginResultFilter,
    start_date: auditStartDate,
    end_date: auditEndDate,
    page_size: 80,
  });
  const operationLogsQueryString = buildQueryString({
    keyword: auditKeyword.trim(),
    resource_code: operationResourceFilter,
    action_code: operationActionFilter,
    start_date: auditStartDate,
    end_date: auditEndDate,
    page_size: 80,
  });

  const { data: loginLogs = { items: [], total: 0, page: 1, page_size: 80 }, isFetching: loginLogsFetching } = useQuery<PagedResponse<LoginLogItem>>({
    queryKey: ["/api/system/login-logs", loginLogsQueryString],
    queryFn: () => apiGet<PagedResponse<LoginLogItem>>(`/api/system/login-logs${loginLogsQueryString}`),
    enabled: tab === "audit-logs" && auditLogType === "login",
  });

  const { data: operationLogs = { items: [], total: 0, page: 1, page_size: 80 }, isFetching: operationLogsFetching } = useQuery<PagedResponse<OperationLogItem>>({
    queryKey: ["/api/system/operation-logs", operationLogsQueryString],
    queryFn: () => apiGet<PagedResponse<OperationLogItem>>(`/api/system/operation-logs${operationLogsQueryString}`),
    enabled: tab === "audit-logs" && auditLogType === "operation",
  });

  const permissionGroups = useMemo(() => {
    const groups = new Map<string, PermissionItem[]>();
    permissions.forEach((permission) => {
      const list = groups.get(permission.module_code) ?? [];
      list.push(permission);
      groups.set(permission.module_code, list);
    });
    return Array.from(groups.entries());
  }, [permissions]);

  const normalizedUserSearchText = userSearchText.trim().toLowerCase();

  const filteredUsers = useMemo(() => {
    if (!normalizedUserSearchText) return users;
    return users.filter((user) =>
      [user.username, user.real_name, user.employee_no]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedUserSearchText)),
    );
  }, [normalizedUserSearchText, users]);

  const filteredContractPermissions = useMemo(() => {
    if (!normalizedUserSearchText) return contractPermissions;
    return contractPermissions.filter((user) =>
      [user.username, user.real_name, user.employee_no]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedUserSearchText)),
    );
  }, [contractPermissions, normalizedUserSearchText]);

  const operationResourceOptions = useMemo(() => {
    const values = new Set(operationLogs.items.map((item) => item.resource_code).filter(Boolean));
    return Array.from(values).sort();
  }, [operationLogs.items]);

  /** scope_matrix 为空时（旧接口或未 JOIN 出数据）用 groups+stores 拼装，避免右侧整表空白 */
  const contractScopeMatrixEffective = useMemo((): ContractScopeMatrixRow[] => {
    const raw = contractPermissionOptions.scope_matrix ?? [];
    if (raw.length > 0) return raw;
    const grp = contractPermissionOptions.groups ?? [];
    const st = contractPermissionOptions.stores ?? [];
    if (!grp.length) return [];
    const nameById = new Map<number, string>();
    for (const s of st) {
      nameById.set(Number(s.id), s.name);
    }
    return grp.map((g) => {
      const sid = g.store_id != null ? Number(g.store_id) : NaN;
      return {
        store_id: Number.isFinite(sid) ? sid : 0,
        store_code: String(g.store_id ?? ""),
        store_name: Number.isFinite(sid) ? nameById.get(sid) ?? `门店#${g.store_id}` : `门店#${g.store_id}`,
        department_code: String(g.department_code ?? "").trim(),
        department_name: String(g.department_name ?? "").trim(),
        group_id: g.id,
        group_code: g.code,
        group_name: g.name,
      };
    });
  }, [contractPermissionOptions.scope_matrix, contractPermissionOptions.groups, contractPermissionOptions.stores]);

  const contractScopeMatrixFiltered = useMemo(() => {
    const matrix = contractScopeMatrixEffective;
    const selected = contractPermissionForm.filter_store_values;
    if (!selected.length) return [];
    const sel = new Set(selected.map(normStoreIdForScope).filter(Boolean));
    return matrix.filter((r) =>
      sel.has(normStoreIdForScope(r.store_id)) &&
      r.department_code.trim() &&
      r.group_code.trim()
    );
  }, [contractPermissionForm.filter_store_values, contractScopeMatrixEffective]);

  const contractScopeMatrixSections = useMemo(() => {
    const filtered = [...contractScopeMatrixFiltered].sort((a, b) => {
      if (a.store_id !== b.store_id) return a.store_id - b.store_id;
      const dc = normScopeCode(a.department_code).localeCompare(normScopeCode(b.department_code));
      if (dc !== 0) return dc;
      return a.group_code.localeCompare(b.group_code);
    });
    const out: { key: string; header: ContractScopeMatrixRow; rows: ContractScopeMatrixRow[] }[] = [];
    for (const row of filtered) {
      const key = `${row.store_id}::${normScopeCode(row.department_code || "")}`;
      const last = out[out.length - 1];
      if (!last || last.key !== key) {
        out.push({ key, header: row, rows: [row] });
      } else {
        last.rows.push(row);
      }
    }
    return out;
  }, [contractScopeMatrixFiltered]);

  const activeScopeDepartment = useMemo(
    () => contractScopeMatrixSections.find((section) => section.key === activeScopeDepartmentKey) ?? null,
    [activeScopeDepartmentKey, contractScopeMatrixSections],
  );

  useEffect(() => {
    if (!activeScopeDepartmentKey) return;
    if (!contractScopeMatrixSections.some((section) => section.key === activeScopeDepartmentKey)) {
      setActiveScopeDepartmentKey(null);
    }
  }, [activeScopeDepartmentKey, contractScopeMatrixSections]);

  const invalidateSystemQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["/api/system/users"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/roles"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/departments"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/data-policies"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/wecom-role-scope-rules"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/meta"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/contract-permissions"] }),
    ]);
  };

  const userMutation = useMutation({
    mutationFn: async () => {
      if (!userForm.username.trim()) throw new Error("请输入工号");
      if (!editingUser && !userForm.password.trim()) throw new Error("请输入初始密码");
      const payload = {
        username: userForm.username,
        real_name: userForm.real_name || null,
        email: userForm.email || null,
        phone: userForm.phone || null,
        status: userForm.status,
        default_store_id: userForm.default_store_id ? Number(userForm.default_store_id) : null,
        employee_no: userForm.employee_no || null,
        is_active: userForm.is_active,
        password: userForm.password,
        role_ids: userForm.role_ids,
        department_assignments: userForm.department_assignments
          .filter((item) => item.store_id && item.department_id)
          .map((item) => ({
            store_id: Number(item.store_id),
            department_id: Number(item.department_id),
            post_id: item.post_id ? Number(item.post_id) : null,
            is_primary: item.is_primary,
          })),
      };

      if (editingUser) {
        return apiPut(`/api/system/users/${editingUser.user_id}`, payload);
      }
      return apiPost("/api/system/users", payload);
    },
    onSuccess: async () => {
      await invalidateSystemQueries();
      setUserDialogOpen(false);
      setEditingUser(null);
      setUserForm(emptyUserForm);
      toast({ title: "用户配置已保存" });
    },
    onError: (error: Error) => {
      toast({ title: "保存用户失败", description: error.message, variant: "destructive" });
    },
  });

  const roleMutation = useMutation({
    mutationFn: async () => {
      if (!roleForm.role_code.trim() || !roleForm.role_name.trim()) throw new Error("请填写角色编码和名称");
      const payload = {
        role_code: roleForm.role_code,
        role_name: roleForm.role_name,
        role_level: Number(roleForm.role_level || 0),
        is_system: roleForm.is_system,
        is_active: roleForm.is_active,
        permission_ids: roleForm.permission_ids,
      };
      if (editingRole) {
        return apiPut(`/api/system/roles/${editingRole.id}`, payload);
      }
      return apiPost("/api/system/roles", payload);
    },
    onSuccess: async () => {
      await invalidateSystemQueries();
      setRoleDialogOpen(false);
      setEditingRole(null);
      setRoleForm(emptyRoleForm);
      toast({ title: "角色配置已保存" });
    },
    onError: (error: Error) => {
      toast({ title: "保存角色失败", description: error.message, variant: "destructive" });
    },
  });

  const departmentMutation = useMutation({
    mutationFn: async () => {
      if (!departmentForm.store_id) throw new Error("请选择所属门店");
      if (!departmentForm.dept_code.trim() || !departmentForm.dept_name.trim()) throw new Error("请填写部门编码和名称");
      const payload = {
        store_id: Number(departmentForm.store_id),
        dept_code: departmentForm.dept_code,
        dept_name: departmentForm.dept_name,
        manager_user_id: departmentForm.manager_user_id ? Number(departmentForm.manager_user_id) : null,
        is_active: departmentForm.is_active,
      };
      if (editingDepartment) {
        return apiPut(`/api/system/departments/${editingDepartment.id}`, payload);
      }
      return apiPost("/api/system/departments", payload);
    },
    onSuccess: async () => {
      await invalidateSystemQueries();
      setDepartmentDialogOpen(false);
      setEditingDepartment(null);
      setDepartmentForm(emptyDepartmentForm);
      toast({ title: "部门配置已保存" });
    },
    onError: (error: Error) => {
      toast({ title: "保存部门失败", description: error.message, variant: "destructive" });
    },
  });

  const syncDepartmentsMutation = useMutation({
    mutationFn: () => apiPost<{ message: string; created: number; updated: number; skipped: number }>("/api/system/departments/sync-from-counter-groups", {}),
    onSuccess: async (result) => {
      await invalidateSystemQueries();
      toast({
        title: "部门同步完成",
        description: `新增 ${result.created} 个，更新 ${result.updated} 个，跳过 ${result.skipped} 个`,
      });
    },
    onError: (error: Error) => {
      toast({ title: "同步部门失败", description: error.message, variant: "destructive" });
    },
  });

  const policyMutation = useMutation({
    mutationFn: async () => {
      if (!policyForm.subject_id) throw new Error("请选择授权主体");
      const payload = {
        subject_type: policyForm.subject_type,
        subject_id: Number(policyForm.subject_id),
        resource_code: policyForm.resource_code,
        action_code: policyForm.action_code,
        scope_mode: policyForm.scope_mode,
        effect: policyForm.effect,
        priority: Number(policyForm.priority || 100),
        is_active: policyForm.is_active,
        source_type: policyForm.source_type,
        source_system: policyForm.source_system,
        external_scope_id: policyForm.external_scope_id || null,
        external_scope_name: policyForm.external_scope_name || null,
        items: buildPolicyItems(policyForm),
      };
      if (editingPolicy) {
        return apiPut(`/api/system/data-policies/${editingPolicy.id}`, payload);
      }
      return apiPost("/api/system/data-policies", payload);
    },
    onSuccess: async () => {
      await invalidateSystemQueries();
      setPolicyDialogOpen(false);
      setEditingPolicy(null);
      setPolicyForm(emptyPolicyForm);
      toast({ title: "数据策略已保存" });
    },
    onError: (error: Error) => {
      toast({ title: "保存策略失败", description: error.message, variant: "destructive" });
    },
  });

  const contractPermissionMutation = useMutation({
    mutationFn: async () => {
      if (!editingContractPermission) throw new Error("请选择人员");
      const payload = {
        enabled: contractPermissionForm.enabled,
        scope_mode: contractPermissionForm.scope_mode,
        store_values: uniqueByNorm(contractPermissionForm.store_values, normStoreIdForScope),
        department_values: uniqueByNorm(contractPermissionForm.department_values),
        group_values: uniqueByNorm(contractPermissionForm.group_values),
      };
      return apiPut(`/api/system/contract-permissions/${editingContractPermission.user_id}`, payload);
    },
    onSuccess: async () => {
      await invalidateSystemQueries();
      setContractPermissionDialogOpen(false);
      setEditingContractPermission(null);
      setContractPermissionForm(emptyContractPermissionForm);
      toast({ title: "业务数据范围已保存" });
    },
    onError: (error: Error) => {
      toast({ title: "保存业务数据范围失败", description: error.message, variant: "destructive" });
    },
  });

  const wecomRuleMutation = useMutation({
    mutationFn: async () => {
      if (!wecomRuleForm.rule_name.trim()) throw new Error("请输入规则名称");
      const payload = {
        rule_name: wecomRuleForm.rule_name.trim(),
        corp_id: wecomRuleForm.corp_id.trim() || null,
        priority: Number(wecomRuleForm.priority || 100),
        match_mode: wecomRuleForm.match_mode,
        wecom_userids: splitValues(wecomRuleForm.wecom_userids),
        name_keywords: splitValues(wecomRuleForm.name_keywords),
        department_keywords: splitValues(wecomRuleForm.department_keywords),
        position_keywords: splitValues(wecomRuleForm.position_keywords),
        role_codes: wecomRuleForm.role_codes,
        scope_mode: wecomRuleForm.scope_mode,
        scope_dimensions: wecomRuleForm.scope_mode === "CUSTOM" ? parseScopeDimensions(wecomRuleForm.scope_dimensions) : {},
        is_active: wecomRuleForm.is_active,
        remark: wecomRuleForm.remark.trim() || null,
      };
      if (editingWeComRule) {
        return apiPut(`/api/system/wecom-role-scope-rules/${editingWeComRule.id}`, payload);
      }
      return apiPost("/api/system/wecom-role-scope-rules", payload);
    },
    onSuccess: async () => {
      await invalidateSystemQueries();
      setWecomRuleDialogOpen(false);
      setEditingWeComRule(null);
      setWecomRuleForm(emptyWeComRuleForm);
      toast({ title: "企微授权规则已保存" });
    },
    onError: (error: Error) => {
      toast({ title: "保存企微授权规则失败", description: error.message, variant: "destructive" });
    },
  });

  const deleteWecomRuleMutation = useMutation({
    mutationFn: async (rule: WeComRoleScopeRule) => {
      return apiDelete(`/api/system/wecom-role-scope-rules/${rule.id}`);
    },
    onSuccess: async () => {
      await invalidateSystemQueries();
      toast({ title: "企微授权规则已删除" });
    },
    onError: (error: Error) => {
      toast({ title: "删除企微授权规则失败", description: error.message, variant: "destructive" });
    },
  });

  const openCreateUser = () => {
    setEditingUser(null);
    setUserForm({
      ...emptyUserForm,
      department_assignments: [{ store_id: "", department_id: "", post_id: "", is_primary: true }],
    });
    setUserDialogOpen(true);
  };

  const openEditUser = (user: UserItem) => {
    setEditingUser(user);
    setUserForm({
      username: user.username,
      real_name: user.real_name ?? "",
      email: user.email ?? "",
      phone: user.phone ?? "",
      status: user.status,
      default_store_id: user.default_store_id ? String(user.default_store_id) : "",
      employee_no: user.employee_no ?? "",
      is_active: user.is_active,
      password: "",
      role_ids: user.role_ids,
      department_assignments: (user.department_assignments.length ? user.department_assignments : [{ store_id: 0, department_id: 0, post_id: null, is_primary: true }]).map((item) => ({
        store_id: item.store_id ? String(item.store_id) : "",
        department_id: item.department_id ? String(item.department_id) : "",
        post_id: item.post_id ? String(item.post_id) : "",
        is_primary: item.is_primary,
      })),
    });
    setUserDialogOpen(true);
  };

  const openCreateRole = () => {
    setEditingRole(null);
    setRoleForm(emptyRoleForm);
    setRoleDialogOpen(true);
  };

  const openEditRole = (role: RoleItem) => {
    setEditingRole(role);
    setRoleForm({
      role_code: role.role_code,
      role_name: role.role_name,
      role_level: String(role.role_level),
      is_system: role.is_system,
      is_active: role.is_active,
      permission_ids: role.permission_ids,
    });
    setRoleDialogOpen(true);
  };

  const openCreateDepartment = () => {
    setEditingDepartment(null);
    setDepartmentForm(emptyDepartmentForm);
    setDepartmentDialogOpen(true);
  };

  const openEditDepartment = (department: DepartmentItem) => {
    setEditingDepartment(department);
    setDepartmentForm({
      store_id: String(department.store_id),
      dept_code: department.dept_code,
      dept_name: department.dept_name,
      manager_user_id: department.manager_user_id ? String(department.manager_user_id) : "",
      is_active: department.is_active,
    });
    setDepartmentDialogOpen(true);
  };

  const openCreatePolicy = () => {
    setEditingPolicy(null);
    setPolicyForm(emptyPolicyForm);
    setPolicyDialogOpen(true);
  };

  const openEditPolicy = (policy: DataPolicy) => {
    const itemsByType = (type: string) =>
      policy.items.filter((item) => item.dimension_type === type).map((item) => item.dimension_value).join(", ");
    setEditingPolicy(policy);
    setPolicyForm({
      subject_type: policy.subject_type,
      subject_id: String(policy.subject_id),
      resource_code: policy.resource_code,
      action_code: policy.action_code,
      scope_mode: policy.scope_mode,
      effect: policy.effect,
      priority: String(policy.priority),
      is_active: policy.is_active,
      store_values: itemsByType("store"),
      department_values: itemsByType("department"),
      group_values: itemsByType("group"),
      floor_values: itemsByType("floor"),
      unit_values: itemsByType("unit"),
      supplier_values: itemsByType("supplier"),
      brand_values: itemsByType("brand"),
      category_values: itemsByType("category"),
      source_type: policy.source_type || "MANUAL",
      source_system: policy.source_system || "shopview",
      external_scope_id: policy.external_scope_id || "",
      external_scope_name: policy.external_scope_name || "",
    });
    setPolicyDialogOpen(true);
  };

  const openEditContractPermission = (user: ContractPermissionUser) => {
    setEditingContractPermission(user);
    const tabOn = user.scope_tab_active ?? user.has_contract_view;
    const mode = user.manual_scope_mode ?? user.scope_mode ?? "CUSTOM";
    const storeValues = uniqueByNorm((user.manual_store_values ?? []).map(normStoreIdForScope).filter(Boolean), normStoreIdForScope);
    const deptValues = uniqueByNorm(user.manual_department_values ?? []);
    const groupValues = uniqueByNorm(user.manual_group_values ?? []);
    const filterStores = new Set(storeValues);
    for (const row of contractScopeMatrixEffective) {
      const storeId = normStoreIdForScope(row.store_id);
      if (!storeId) continue;
      if (deptValues.some((code) => normScopeCode(code) === normScopeCode(row.department_code))) {
        filterStores.add(storeId);
      }
      if (groupValues.some((code) => normScopeCode(code) === normScopeCode(row.group_code))) {
        filterStores.add(storeId);
      }
    }
    setContractPermissionForm({
      enabled: tabOn,
      scope_mode: mode === "ALL" || mode === "CUSTOM" ? mode : "CUSTOM",
      filter_store_values: Array.from(filterStores),
      store_values: storeValues,
      department_values: deptValues,
      group_values: groupValues,
    });
    setContractPermissionDialogOpen(true);
  };

  const openCreateWecomRule = () => {
    setEditingWeComRule(null);
    setWecomRuleForm(emptyWeComRuleForm);
    setWecomRuleDialogOpen(true);
  };

  const openEditWecomRule = (rule: WeComRoleScopeRule) => {
    setEditingWeComRule(rule);
    setWecomRuleForm({
      rule_name: rule.rule_name,
      corp_id: rule.corp_id ?? "",
      priority: String(rule.priority),
      match_mode: rule.match_mode,
      wecom_userids: joinValues(rule.wecom_userids),
      name_keywords: joinValues(rule.name_keywords),
      department_keywords: joinValues(rule.department_keywords),
      position_keywords: joinValues(rule.position_keywords),
      role_codes: rule.role_codes ?? [],
      scope_mode: rule.scope_mode,
      scope_dimensions: JSON.stringify(rule.scope_dimensions ?? {}, null, 2),
      is_active: rule.is_active,
      remark: rule.remark ?? "",
    });
    setWecomRuleDialogOpen(true);
  };

  const rowsForStore = (storeId: string) =>
    contractScopeMatrixEffective.filter((row) => normStoreIdForScope(row.store_id) === storeId);

  const rowsForDepartment = (departmentCode: string, storeIds?: Set<string>) =>
    contractScopeMatrixEffective.filter((row) => {
      if (normScopeCode(row.department_code) !== normScopeCode(departmentCode)) return false;
      return !storeIds || storeIds.has(normStoreIdForScope(row.store_id));
    });

  const removeRowsFromScope = (values: string[], rows: ContractScopeMatrixRow[], field: "department" | "group") => {
    const drop = new Set(rows.map((row) => normScopeCode(field === "department" ? row.department_code : row.group_code)));
    return values.filter((value) => !drop.has(normScopeCode(value)));
  };

  const departmentCodesForRows = (rows: ContractScopeMatrixRow[]) =>
    uniqueByNorm(rows.map((row) => row.department_code).filter((code) => code.trim()));

  const groupCodesForRows = (rows: ContractScopeMatrixRow[]) =>
    uniqueByNorm(rows.map((row) => row.group_code).filter((code) => code.trim()));

  const toggleContractScopeValue = (field: "store_values" | "department_values" | "group_values", value: string, checked: boolean) => {
    const target = normScopeCode(value);
    const storeTarget = normStoreIdForScope(value);
    setContractPermissionForm((prev) => {
      if (field === "store_values") {
        const storeRows = rowsForStore(storeTarget);
        const nextFilterStores = checked
          ? uniqueByNorm([...prev.filter_store_values, storeTarget], normStoreIdForScope)
          : prev.filter_store_values.filter((item) => normStoreIdForScope(item) !== storeTarget);
        const nextStores = checked
          ? uniqueByNorm([...prev.store_values.filter((item) => normStoreIdForScope(item) !== storeTarget), storeTarget], normStoreIdForScope)
          : prev.store_values.filter((item) => normStoreIdForScope(item) !== storeTarget);
        return {
          ...prev,
          filter_store_values: nextFilterStores,
          store_values: nextStores,
          department_values: removeRowsFromScope(prev.department_values, storeRows, "department"),
          group_values: removeRowsFromScope(prev.group_values, storeRows, "group"),
        };
      }
      const nextVals = checked
        ? Array.from(new Set([...prev[field].filter((item) => normScopeCode(item) !== target), value]))
        : prev[field].filter((item) => normScopeCode(item) !== target);
      return { ...prev, [field]: nextVals };
    });
    if (field === "store_values" && !checked) {
      setActiveScopeDepartmentKey((key) => {
        if (!key) return key;
        return key.startsWith(`${storeTarget}::`) ? null : key;
      });
    }
  };

  const clearDepartmentSelectionForFilteredStores = () => {
    const storeIds = new Set(contractPermissionForm.filter_store_values.map(normStoreIdForScope).filter(Boolean));
    const rows = contractScopeMatrixEffective.filter((row) => storeIds.has(normStoreIdForScope(row.store_id)));
    setContractPermissionForm((prev) => ({
      ...prev,
      store_values: prev.store_values.filter((storeId) => !storeIds.has(normStoreIdForScope(storeId))),
      department_values: removeRowsFromScope(prev.department_values, rows, "department"),
      group_values: removeRowsFromScope(prev.group_values, rows, "group"),
    }));
  };

  const toggleDepartmentScope = (section: { header: ContractScopeMatrixRow; rows: ContractScopeMatrixRow[] }, checked: boolean) => {
    const departmentCode = section.header.department_code;
    if (!departmentCode.trim()) return;
    const deptNorm = normScopeCode(departmentCode);
    const sectionStoreIds = new Set(section.rows.map((row) => normStoreIdForScope(row.store_id)));
    setContractPermissionForm((prev) => {
      const storeGrantsInSection = prev.store_values.filter((storeId) => sectionStoreIds.has(normStoreIdForScope(storeId)));
      if (checked) {
        return {
          ...prev,
          department_values: uniqueByNorm([...prev.department_values.filter((code) => normScopeCode(code) !== deptNorm), departmentCode]),
          group_values: removeRowsFromScope(prev.group_values, section.rows, "group"),
        };
      }
      if (storeGrantsInSection.length) {
        let nextDepartments = prev.department_values.filter((code) => normScopeCode(code) !== deptNorm);
        let nextGroups = removeRowsFromScope(prev.group_values, section.rows, "group");
        for (const storeId of storeGrantsInSection.map(normStoreIdForScope)) {
          const storeRows = rowsForStore(storeId);
          nextDepartments = uniqueByNorm([
            ...nextDepartments,
            ...departmentCodesForRows(storeRows.filter((row) => normScopeCode(row.department_code) !== deptNorm)),
          ]);
          nextGroups = uniqueByNorm([
            ...nextGroups,
            ...groupCodesForRows(storeRows.filter((row) => !row.department_code.trim())),
          ]);
        }
        return {
          ...prev,
          store_values: prev.store_values.filter((storeId) => !sectionStoreIds.has(normStoreIdForScope(storeId))),
          department_values: nextDepartments,
          group_values: nextGroups,
        };
      }
      return {
        ...prev,
        department_values: prev.department_values.filter((code) => normScopeCode(code) !== deptNorm),
        group_values: removeRowsFromScope(prev.group_values, section.rows, "group"),
      };
    });
  };

  const toggleGroupScope = (row: ContractScopeMatrixRow, checked: boolean) => {
    const storeId = normStoreIdForScope(row.store_id);
    const deptCode = row.department_code;
    const deptNorm = normScopeCode(deptCode);
    const groupNorm = normScopeCode(row.group_code);
    setContractPermissionForm((prev) => {
      if (checked) {
        return {
          ...prev,
          group_values: uniqueByNorm([...prev.group_values.filter((code) => normScopeCode(code) !== groupNorm), row.group_code]),
        };
      }

      const storeGranted = prev.store_values.some((value) => normStoreIdForScope(value) === storeId);
      const deptGranted = deptCode.trim() && prev.department_values.some((value) => normScopeCode(value) === deptNorm);
      if (storeGranted) {
        const storeRows = rowsForStore(storeId);
        const sameDeptRows = deptCode.trim()
          ? storeRows.filter((item) => normScopeCode(item.department_code) === deptNorm)
          : storeRows.filter((item) => !item.department_code.trim());
        return {
          ...prev,
          store_values: prev.store_values.filter((value) => normStoreIdForScope(value) !== storeId),
          department_values: uniqueByNorm([
            ...prev.department_values,
            ...departmentCodesForRows(storeRows.filter((item) => item.department_code.trim() && normScopeCode(item.department_code) !== deptNorm)),
          ]),
          group_values: uniqueByNorm([
            ...removeRowsFromScope(prev.group_values, sameDeptRows, "group"),
            ...groupCodesForRows(sameDeptRows.filter((item) => normScopeCode(item.group_code) !== groupNorm)),
            ...groupCodesForRows(storeRows.filter((item) => !item.department_code.trim() && normScopeCode(item.group_code) !== groupNorm)),
          ]),
        };
      }
      if (deptGranted) {
        const deptRows = rowsForDepartment(deptCode, new Set([storeId]));
        return {
          ...prev,
          department_values: prev.department_values.filter((value) => normScopeCode(value) !== deptNorm),
          group_values: uniqueByNorm([
            ...removeRowsFromScope(prev.group_values, deptRows, "group"),
            ...groupCodesForRows(deptRows.filter((item) => normScopeCode(item.group_code) !== groupNorm)),
          ]),
        };
      }
      return {
        ...prev,
        group_values: prev.group_values.filter((value) => normScopeCode(value) !== groupNorm),
      };
    });
  };

  const selectAllGroupsInSection = (rows: ContractScopeMatrixRow[]) => {
    const codes = rows.map((r) => r.group_code);
    setContractPermissionForm((prev) => ({
      ...prev,
      group_values: uniqueByNorm([...prev.group_values, ...codes]),
    }));
  };

  const currentSubjectOptions = policyForm.subject_type === "ROLE" ? meta?.roles ?? [] : meta?.users ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">用户角色及范围定义</h1>
          <p className="text-slate-600 mt-1">统一维护账号、角色、组织、功能权限和业务数据范围。</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">用户数</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-2xl font-bold">{users.length}</span>
            <Users className="h-5 w-5 text-blue-600" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">角色数</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-2xl font-bold">{roles.length}</span>
            <Shield className="h-5 w-5 text-emerald-600" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">部门数</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-2xl font-bold">{departments.length}</span>
            <Building2 className="h-5 w-5 text-amber-600" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">策略数</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-2xl font-bold">{policies.length}</span>
            <Filter className="h-5 w-5 text-purple-600" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">业务范围授权</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-2xl font-bold">{contractPermissions.filter((item) => item.has_contract_view).length}</span>
            <FileText className="h-5 w-5 text-sky-600" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">企微规则</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-2xl font-bold">{wecomRules.length}</span>
            <Shield className="h-5 w-5 text-teal-600" />
          </CardContent>
        </Card>
      </div>

      <Tabs value={tab} onValueChange={(value) => setTab(value as SystemConfigTab)}>
        <TabsList className="grid w-full grid-cols-2 gap-1 h-auto rounded-md border border-slate-200 bg-slate-100 p-1 md:grid-cols-7">
          <TabsTrigger className="h-11 rounded border border-transparent text-base data-[state=active]:border-slate-300 data-[state=active]:bg-white data-[state=active]:font-semibold data-[state=active]:shadow-sm" value="users">用户</TabsTrigger>
          <TabsTrigger className="h-11 rounded border border-transparent text-base data-[state=active]:border-slate-300 data-[state=active]:bg-white data-[state=active]:font-semibold data-[state=active]:shadow-sm" value="roles">角色</TabsTrigger>
          <TabsTrigger className="h-11 rounded border border-transparent text-base data-[state=active]:border-slate-300 data-[state=active]:bg-white data-[state=active]:font-semibold data-[state=active]:shadow-sm" value="departments">部门定义</TabsTrigger>
          <TabsTrigger className="h-11 rounded border border-transparent text-base data-[state=active]:border-slate-300 data-[state=active]:bg-white data-[state=active]:font-semibold data-[state=active]:shadow-sm" value="contract-permissions">业务范围</TabsTrigger>
          <TabsTrigger className="h-11 rounded border border-transparent text-base data-[state=active]:border-slate-300 data-[state=active]:bg-white data-[state=active]:font-semibold data-[state=active]:shadow-sm" value="wecom-rules">企微规则</TabsTrigger>
          <TabsTrigger className="h-11 rounded border border-transparent text-base data-[state=active]:border-slate-300 data-[state=active]:bg-white data-[state=active]:font-semibold data-[state=active]:shadow-sm" value="policies">高级策略</TabsTrigger>
          <TabsTrigger className="h-11 rounded border border-transparent text-base data-[state=active]:border-slate-300 data-[state=active]:bg-white data-[state=active]:font-semibold data-[state=active]:shadow-sm" value="audit-logs">日志审计</TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                className="pl-9"
                placeholder="按工号或姓名筛选"
                value={userSearchText}
                onChange={(event) => setUserSearchText(event.target.value)}
              />
            </div>
            <Button onClick={openCreateUser}><Plus className="mr-2 h-4 w-4" />新增用户</Button>
          </div>
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>工号</TableHead>
                    <TableHead>姓名</TableHead>
                    <TableHead>角色</TableHead>
                    <TableHead>默认门店</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUsers.map((user) => (
                    <TableRow key={user.user_id}>
                      <TableCell>{user.username}</TableCell>
                      <TableCell>{user.real_name || "-"}</TableCell>
                      <TableCell>{user.role_names.join(" / ") || "-"}</TableCell>
                      <TableCell>{stores.find((store) => store.storeId === user.default_store_id)?.storeName || "-"}</TableCell>
                      <TableCell>
                        <Badge variant={user.is_active ? "default" : "secondary"}>{user.status}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline" onClick={() => openEditUser(user)}>编辑</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roles" className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreateRole}><Plus className="mr-2 h-4 w-4" />新增角色</Button>
          </div>
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>角色编码</TableHead>
                    <TableHead>角色名称</TableHead>
                    <TableHead>级别</TableHead>
                    <TableHead>权限数</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {roles.map((role) => (
                    <TableRow key={role.id}>
                      <TableCell>{role.role_code}</TableCell>
                      <TableCell>{role.role_name}</TableCell>
                      <TableCell>{role.role_level}</TableCell>
                      <TableCell>{role.permission_ids.length}</TableCell>
                      <TableCell>
                        <Badge variant={role.is_active ? "default" : "secondary"}>{role.is_active ? "启用" : "停用"}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline" onClick={() => openEditRole(role)}>编辑</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="departments" className="space-y-4">
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => syncDepartmentsMutation.mutate()} disabled={syncDepartmentsMutation.isPending}>
              {syncDepartmentsMutation.isPending ? "同步中..." : "从柜组同步部门"}
            </Button>
            <Button onClick={openCreateDepartment}><Plus className="mr-2 h-4 w-4" />新增部门</Button>
          </div>
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>门店</TableHead>
                    <TableHead>部门编码</TableHead>
                    <TableHead>部门名称</TableHead>
                    <TableHead>主管</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {departments.map((department) => (
                    <TableRow key={department.id}>
                      <TableCell>{department.store_name || "-"}</TableCell>
                      <TableCell>{department.dept_code}</TableCell>
                      <TableCell>{department.dept_name}</TableCell>
                      <TableCell>{department.manager_name || "-"}</TableCell>
                      <TableCell>
                        <Badge variant={department.is_active ? "default" : "secondary"}>{department.is_active ? "启用" : "停用"}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline" onClick={() => openEditDepartment(department)}>编辑</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="contract-permissions" className="space-y-4">
          <Card>
            <CardContent className="pt-6">
              <div className="relative mb-4 w-full sm:max-w-sm">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  className="pl-9"
                  placeholder="按工号或姓名筛选"
                  value={userSearchText}
                  onChange={(event) => setUserSearchText(event.target.value)}
                />
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>工号</TableHead>
                    <TableHead>姓名</TableHead>
                    <TableHead>合同功能</TableHead>
                    <TableHead>范围</TableHead>
                    <TableHead>来源</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredContractPermissions.map((user) => (
                    <TableRow key={user.user_id}>
                      <TableCell>{user.username}</TableCell>
                      <TableCell>{user.real_name || "-"}</TableCell>
                      <TableCell>
                        <Badge variant={user.has_contract_view ? "default" : "secondary"}>{user.has_contract_view ? "已开通" : "未开通"}</Badge>
                      </TableCell>
                      <TableCell className="max-w-lg">
                        {user.scope_mode === "ALL" ? "全部业务数据" : [
                          user.store_values.length ? `门店 ${user.store_values.join(", ")}` : "",
                          user.department_values.length ? `部门 ${user.department_values.join(", ")}` : "",
                          user.group_values.length ? `柜组 ${user.group_values.join(", ")}` : "",
                        ].filter(Boolean).join("；") || "-"}
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1 text-xs">
                          <Badge variant="outline">手工 {user.manual_scope_count}</Badge>
                          <Badge variant="secondary">ERP {user.erp_scope_count}</Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={user.is_active ? "default" : "secondary"}>{user.status}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline" onClick={() => openEditContractPermission(user)}>配置</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="wecom-rules" className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreateWecomRule}><Plus className="mr-2 h-4 w-4" />新增企微规则</Button>
          </div>
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>规则</TableHead>
                    <TableHead>匹配条件</TableHead>
                    <TableHead>角色</TableHead>
                    <TableHead>数据范围</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {wecomRules.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell>
                        <div className="font-medium">{rule.rule_name}</div>
                        <div className="text-xs text-muted-foreground">优先级 {rule.priority} · {rule.match_mode === "ANY" ? "任一匹配" : "全部匹配"}</div>
                      </TableCell>
                      <TableCell className="max-w-md">
                        {[
                          rule.wecom_userids.length ? `用户 ${rule.wecom_userids.join(", ")}` : "",
                          rule.name_keywords.length ? `姓名 ${rule.name_keywords.join(", ")}` : "",
                          rule.department_keywords.length ? `部门 ${rule.department_keywords.join(", ")}` : "",
                          rule.position_keywords.length ? `岗位 ${rule.position_keywords.join(", ")}` : "",
                        ].filter(Boolean).join("；") || "-"}
                      </TableCell>
                      <TableCell>{rule.role_codes.join(" / ") || "-"}</TableCell>
                      <TableCell className="max-w-md">
                        {rule.scope_mode === "ALL"
                          ? "全部业务数据"
                          : rule.scope_mode === "NONE"
                            ? "不生成数据范围"
                            : Object.entries(rule.scope_dimensions || {}).map(([key, values]) => `${key}:${values.join(",")}`).join("；") || "-"}
                      </TableCell>
                      <TableCell>
                        <Badge variant={rule.is_active ? "default" : "secondary"}>{rule.is_active ? "启用" : "停用"}</Badge>
                      </TableCell>
                      <TableCell className="text-right space-x-2">
                        <Button size="sm" variant="outline" onClick={() => openEditWecomRule(rule)}>编辑</Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            if (window.confirm(`确认删除企微规则「${rule.rule_name}」？`)) {
                              deleteWecomRuleMutation.mutate(rule);
                            }
                          }}
                        >
                          删除
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!wecomRules.length ? (
                    <TableRow>
                      <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                        暂无企微规则。新增规则后，企业微信同步会优先使用这里的配置。
                      </TableCell>
                    </TableRow>
                  ) : null}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="policies" className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreatePolicy}><Plus className="mr-2 h-4 w-4" />新增策略</Button>
          </div>
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>主体</TableHead>
                    <TableHead>资源</TableHead>
                    <TableHead>动作</TableHead>
                    <TableHead>来源</TableHead>
                    <TableHead>范围</TableHead>
                    <TableHead>维度项</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {policies.map((policy) => (
                    <TableRow key={policy.id}>
                      <TableCell>{policy.subject_type} / {policy.subject_name || policy.subject_id}</TableCell>
                      <TableCell>{policy.resource_code}</TableCell>
                      <TableCell>{policy.action_code}</TableCell>
                      <TableCell>
                        <div className="space-y-1 text-xs">
                          <Badge variant={policy.source_type === "ERP" ? "secondary" : "outline"}>{policy.source_type || "MANUAL"}</Badge>
                          <div className="text-muted-foreground">{policy.external_scope_name || policy.source_system || "shopview"}</div>
                        </div>
                      </TableCell>
                      <TableCell>{policy.scope_mode}</TableCell>
                      <TableCell>{policy.items.map((item) => `${item.dimension_type}:${item.dimension_value}`).join("，") || "-"}</TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline" onClick={() => openEditPolicy(policy)}>编辑</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit-logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-5 w-5" />
                日志审计
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-[180px_minmax(220px,1fr)_160px_160px_180px_120px]">
                <Select value={auditLogType} onValueChange={(value) => setAuditLogType(value as "login" | "operation")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="login">登录日志</SelectItem>
                    <SelectItem value="operation">操作日志</SelectItem>
                  </SelectContent>
                </Select>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    className="pl-9"
                    placeholder={auditLogType === "login" ? "用户、姓名、登录账号" : "用户、姓名、模块、目标"}
                    value={auditKeyword}
                    onChange={(event) => setAuditKeyword(event.target.value)}
                  />
                </div>
                <Input type="date" value={auditStartDate} onChange={(event) => setAuditStartDate(event.target.value)} />
                <Input type="date" value={auditEndDate} onChange={(event) => setAuditEndDate(event.target.value)} />
                {auditLogType === "login" ? (
                  <Select value={loginResultFilter} onValueChange={setLoginResultFilter}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">全部结果</SelectItem>
                      <SelectItem value="SUCCESS">成功</SelectItem>
                      <SelectItem value="FAILED">失败</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Select value={operationActionFilter} onValueChange={setOperationActionFilter}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">全部动作</SelectItem>
                      <SelectItem value="enter">进入模块</SelectItem>
                      <SelectItem value="create">新增</SelectItem>
                      <SelectItem value="update">修改</SelectItem>
                      <SelectItem value="delete">删除</SelectItem>
                      <SelectItem value="login">登录</SelectItem>
                      <SelectItem value="logout">退出</SelectItem>
                    </SelectContent>
                  </Select>
                )}
                <Button
                  variant="outline"
                  onClick={() => {
                    queryClient.invalidateQueries({ queryKey: ["/api/system/login-logs"] });
                    queryClient.invalidateQueries({ queryKey: ["/api/system/operation-logs"] });
                  }}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />刷新
                </Button>
              </div>

              {auditLogType === "operation" ? (
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant={operationResourceFilter === "ALL" ? "default" : "outline"}
                    onClick={() => setOperationResourceFilter("ALL")}
                  >
                    全部模块
                  </Button>
                  {operationResourceOptions.map((resource) => (
                    <Button
                      key={resource}
                      size="sm"
                      variant={operationResourceFilter === resource ? "default" : "outline"}
                      onClick={() => setOperationResourceFilter(resource)}
                    >
                      {resource}
                    </Button>
                  ))}
                </div>
              ) : null}

              {auditLogType === "login" ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>时间</TableHead>
                      <TableHead>用户</TableHead>
                      <TableHead>登录标识</TableHead>
                      <TableHead>方式</TableHead>
                      <TableHead>结果</TableHead>
                      <TableHead>终端</TableHead>
                      <TableHead>IP</TableHead>
                      <TableHead>客户端</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loginLogs.items.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="whitespace-nowrap">{formatDateTime(log.created_at)}</TableCell>
                        <TableCell>{log.real_name || log.username || "-"}</TableCell>
                        <TableCell>{log.identifier || "-"}</TableCell>
                        <TableCell>{log.identity_type || "-"}</TableCell>
                        <TableCell>
                          <Badge variant={log.login_result === "SUCCESS" ? "default" : "destructive"}>
                            {log.login_result === "SUCCESS" ? "成功" : "失败"}
                          </Badge>
                        </TableCell>
                        <TableCell>{loginDeviceLabel[log.device_type || "UNKNOWN"] || log.device_type || "未知"}</TableCell>
                        <TableCell>{log.ip_address || "-"}</TableCell>
                        <TableCell className="max-w-xs truncate" title={log.user_agent || ""}>{log.user_agent || "-"}</TableCell>
                      </TableRow>
                    ))}
                    {!loginLogs.items.length ? (
                      <TableRow>
                        <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                          {loginLogsFetching ? "加载中..." : "暂无登录日志"}
                        </TableCell>
                      </TableRow>
                    ) : null}
                  </TableBody>
                </Table>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>时间</TableHead>
                      <TableHead>用户</TableHead>
                      <TableHead>模块</TableHead>
                      <TableHead>动作</TableHead>
                      <TableHead>目标</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>IP</TableHead>
                      <TableHead>路径</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {operationLogs.items.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="whitespace-nowrap">{formatDateTime(log.created_at)}</TableCell>
                        <TableCell>{log.real_name || log.username || "-"}</TableCell>
                        <TableCell>{log.resource_code}</TableCell>
                        <TableCell>{log.action_code === "enter" ? "进入模块" : log.action_code}</TableCell>
                        <TableCell>{String(log.detail?.module_name || log.target_id || "-")}</TableCell>
                        <TableCell>{String(log.detail?.status_code ?? "-")}</TableCell>
                        <TableCell>{log.ip_address || "-"}</TableCell>
                        <TableCell className="max-w-xs truncate" title={String(log.detail?.path || "")}>
                          {String(log.detail?.path || "-")}
                        </TableCell>
                      </TableRow>
                    ))}
                    {!operationLogs.items.length ? (
                      <TableRow>
                        <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                          {operationLogsFetching ? "加载中..." : "暂无操作日志"}
                        </TableCell>
                      </TableRow>
                    ) : null}
                  </TableBody>
                </Table>
              )}
              <div className="text-sm text-muted-foreground">
                当前显示前 80 条，共 {auditLogType === "login" ? loginLogs.total : operationLogs.total} 条。
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={contractPermissionDialogOpen} onOpenChange={setContractPermissionDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>配置业务数据范围 - {editingContractPermission?.real_name || editingContractPermission?.username}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={contractPermissionForm.enabled}
                  onCheckedChange={(checked) => setContractPermissionForm((prev) => ({ ...prev, enabled: !!checked }))}
                />
                <span className="text-sm">允许查看合同模块（本页对应「合同查看人员」角色及手工业务范围）</span>
              </div>
              {editingContractPermission?.has_contract_view && editingContractPermission?.scope_tab_active === false ? (
                <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-md px-2 py-1.5">
                  该账号仍通过<strong>其他角色</strong>拥有合同查看权限；关闭上方开关只会移除「合同查看人员」角色与本页手工范围，不会在角色管理中改动其它角色。
                </p>
              ) : null}
              {(editingContractPermission?.erp_scope_count ?? 0) > 0 ? (
                <p className="text-xs text-muted-foreground">
                  列表「范围」列可能合并显示 ERP 同步策略；下方勾选框仅编辑<strong>手工维护</strong>的范围（与列表列不完全一致属正常现象）。
                </p>
              ) : null}
            </div>
            <div>
              <Label>统一业务数据范围</Label>
              <Select value={contractPermissionForm.scope_mode} onValueChange={(value) => setContractPermissionForm((prev) => ({ ...prev, scope_mode: value as "ALL" | "CUSTOM" }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="CUSTOM">按门店/部门/柜组</SelectItem>
                  <SelectItem value="ALL">全部业务数据</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {contractPermissionForm.scope_mode === "CUSTOM" && (
              <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-4 items-start">
                <div className="space-y-2">
	                  <Label>筛选门店</Label>
	                  <p className="text-xs text-muted-foreground">勾选门店后默认授权该门店全部部门；需要细分时可在右侧取消部门全选后再勾选部门或柜组。</p>
	                  <div className="border rounded-md p-3 max-h-72 overflow-y-auto space-y-2">
	                    {contractPermissionOptions.stores.map((store) => (
	                      <label key={store.id} className="flex items-center gap-2 text-sm">
	                        <Checkbox
	                          checked={contractPermissionForm.filter_store_values.some((s) => normStoreIdForScope(s) === normStoreIdForScope(store.code))}
	                          onCheckedChange={(checked) => toggleContractScopeValue("store_values", store.code, !!checked)}
	                        />
	                        <span>{store.name}</span>
	                      </label>
                    ))}
                  </div>
                </div>
                <div className="space-y-2 min-w-0">
                  <Label>门店 / 部门 / 柜组（同源：manaframe 关联门店）</Label>
	                  {!contractPermissionForm.filter_store_values.length ? (
	                    <p className="text-xs text-muted-foreground border rounded-md p-3 bg-slate-50">请先勾选左侧门店，表格将列出该门店下的部门与柜组。</p>
	                  ) : contractScopeMatrixFiltered.length === 0 ? (
                    <p className="text-xs text-muted-foreground border rounded-md p-3 bg-slate-50">
                      {contractScopeMatrixEffective.length === 0
                        ? "系统中暂无柜组（manaframe）。请先同步 ERP 后再配置。"
                        : "当前勾选门店在柜组表中没有带部门编码的柜组记录。请核对 manaframe.mfcode、mfpcode 和上级部门。"}
                    </p>
		                  ) : (
		                    <div className="grid grid-cols-1 lg:grid-cols-[minmax(260px,0.8fr)_minmax(320px,1fr)] gap-4">
		                      <div className="space-y-2">
		                        <div className="flex items-center justify-between">
		                          <Label>部门</Label>
		                          <Button type="button" variant="outline" size="sm" className="h-8" onClick={clearDepartmentSelectionForFilteredStores}>
		                            取消部门全选
		                          </Button>
		                        </div>
		                        <div className="border rounded-md max-h-[28rem] overflow-y-auto divide-y">
		                          {contractScopeMatrixSections.map((section) => {
		                            const storeGranted = contractPermissionForm.store_values.some(
		                              (storeId) => normStoreIdForScope(storeId) === normStoreIdForScope(section.header.store_id),
		                            );
		                            const departmentGranted = contractPermissionForm.department_values.some(
		                              (code) => normScopeCode(code) === normScopeCode(section.header.department_code),
		                            );
		                            return (
		                              <div
		                                key={section.key}
		                                className={`flex items-start gap-3 p-3 cursor-pointer ${activeScopeDepartmentKey === section.key ? "bg-slate-100" : "bg-white hover:bg-slate-50"}`}
		                                onClick={() => setActiveScopeDepartmentKey(section.key)}
		                              >
		                                <Checkbox
		                                  checked={storeGranted || departmentGranted}
		                                  onCheckedChange={(checked) => toggleDepartmentScope(section, !!checked)}
		                                  onClick={(event) => event.stopPropagation()}
		                                  aria-label={`部门 ${section.header.department_code}`}
		                                />
		                                <div className="min-w-0 flex-1">
		                                  <div className="text-sm font-medium text-slate-900 truncate">{section.header.department_name.trim() || section.header.department_code}</div>
		                                  <div className="text-xs text-muted-foreground tabular-nums">编码 {section.header.department_code}</div>
		                                  <div className="text-xs text-muted-foreground mt-0.5">{section.header.store_name} · {section.rows.length} 个柜组</div>
		                                </div>
		                              </div>
		                            );
		                          })}
		                        </div>
		                      </div>
		                      <div className="space-y-2">
		                        <div className="flex items-center justify-between">
		                          <Label>柜组</Label>
		                          {activeScopeDepartment ? (
		                            <Button type="button" variant="outline" size="sm" className="h-8" onClick={() => selectAllGroupsInSection(activeScopeDepartment.rows)}>
		                              全选柜组
		                            </Button>
		                          ) : null}
		                        </div>
		                        {!activeScopeDepartment ? (
		                          <p className="text-xs text-muted-foreground border rounded-md p-3 bg-slate-50">请先在中间选择一个部门。</p>
		                        ) : (
		                          <div className="border rounded-md max-h-[28rem] overflow-y-auto divide-y">
		                            {activeScopeDepartment.rows.map((row) => (
		                              <label key={row.group_id} className="flex items-center gap-3 p-3 text-sm">
		                                <Checkbox
		                                  checked={
		                                    contractPermissionForm.store_values.some(
		                                      (storeId) => normStoreIdForScope(storeId) === normStoreIdForScope(row.store_id),
		                                    ) ||
		                                    contractPermissionForm.department_values.some(
		                                      (code) => normScopeCode(code) === normScopeCode(row.department_code),
		                                    ) ||
		                                    contractPermissionForm.group_values.some(
		                                      (code) => normScopeCode(code) === normScopeCode(row.group_code),
		                                    )
		                                  }
		                                  onCheckedChange={(checked) => toggleGroupScope(row, !!checked)}
		                                  aria-label={`柜组 ${row.group_code}`}
		                                />
		                                <span className="font-mono text-[13px] text-slate-900">{row.group_code}</span>
		                                <span className="min-w-0 flex-1 truncate text-slate-600">{row.group_name}</span>
		                              </label>
		                            ))}
		                          </div>
		                        )}
		                      </div>
		                    </div>
		                  )}
                </div>
              </div>
            )}
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setContractPermissionDialogOpen(false)}>取消</Button>
            <Button onClick={() => contractPermissionMutation.mutate()} disabled={contractPermissionMutation.isPending}>
              {contractPermissionMutation.isPending ? "保存中..." : "保存"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={wecomRuleDialogOpen} onOpenChange={setWecomRuleDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingWeComRule ? "编辑企微授权规则" : "新增企微授权规则"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="md:col-span-2">
                <Label>规则名称</Label>
                <Input value={wecomRuleForm.rule_name} onChange={(e) => setWecomRuleForm((prev) => ({ ...prev, rule_name: e.target.value }))} />
              </div>
              <div>
                <Label>优先级</Label>
                <Input type="number" value={wecomRuleForm.priority} onChange={(e) => setWecomRuleForm((prev) => ({ ...prev, priority: e.target.value }))} />
              </div>
              <div>
                <Label>匹配模式</Label>
                <Select value={wecomRuleForm.match_mode} onValueChange={(value) => setWecomRuleForm((prev) => ({ ...prev, match_mode: value as "ALL" | "ANY" }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">全部条件</SelectItem>
                    <SelectItem value="ANY">任一条件</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <Label>企业微信用户ID</Label>
                <Textarea rows={5} value={wecomRuleForm.wecom_userids} onChange={(e) => setWecomRuleForm((prev) => ({ ...prev, wecom_userids: e.target.value }))} />
              </div>
              <div>
                <Label>姓名关键词</Label>
                <Textarea rows={5} value={wecomRuleForm.name_keywords} onChange={(e) => setWecomRuleForm((prev) => ({ ...prev, name_keywords: e.target.value }))} />
              </div>
              <div>
                <Label>部门关键词</Label>
                <Textarea rows={5} value={wecomRuleForm.department_keywords} onChange={(e) => setWecomRuleForm((prev) => ({ ...prev, department_keywords: e.target.value }))} />
              </div>
              <div>
                <Label>岗位关键词</Label>
                <Textarea rows={5} value={wecomRuleForm.position_keywords} onChange={(e) => setWecomRuleForm((prev) => ({ ...prev, position_keywords: e.target.value }))} />
              </div>
            </div>

            <div>
              <Label>系统角色</Label>
              <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 border rounded-md p-3 max-h-56 overflow-y-auto">
                {roles.map((role) => (
                  <label key={role.id} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={wecomRuleForm.role_codes.includes(role.role_code)}
                      onCheckedChange={(checked) => setWecomRuleForm((prev) => ({
                        ...prev,
                        role_codes: checked
                          ? Array.from(new Set([...prev.role_codes, role.role_code]))
                          : prev.role_codes.filter((code) => code !== role.role_code),
                      }))}
                    />
                    <span>{role.role_name}</span>
                    <span className="text-xs text-muted-foreground">{role.role_code}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-[180px_1fr] gap-4">
              <div>
                <Label>数据范围</Label>
                <Select value={wecomRuleForm.scope_mode} onValueChange={(value) => setWecomRuleForm((prev) => ({ ...prev, scope_mode: value as "ALL" | "CUSTOM" | "NONE" }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CUSTOM">自定义范围</SelectItem>
                    <SelectItem value="ALL">全部业务数据</SelectItem>
                    <SelectItem value="NONE">不生成范围</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>范围 JSON</Label>
                <Textarea
                  rows={7}
                  disabled={wecomRuleForm.scope_mode !== "CUSTOM"}
                  value={wecomRuleForm.scope_dimensions}
                  onChange={(e) => setWecomRuleForm((prev) => ({ ...prev, scope_dimensions: e.target.value }))}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-[1fr_180px] gap-4">
              <div>
                <Label>备注</Label>
                <Input value={wecomRuleForm.remark} onChange={(e) => setWecomRuleForm((prev) => ({ ...prev, remark: e.target.value }))} />
              </div>
              <label className="flex items-center gap-2 pt-7 text-sm">
                <Checkbox checked={wecomRuleForm.is_active} onCheckedChange={(checked) => setWecomRuleForm((prev) => ({ ...prev, is_active: !!checked }))} />
                <span>启用</span>
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setWecomRuleDialogOpen(false)}>取消</Button>
            <Button onClick={() => wecomRuleMutation.mutate()} disabled={wecomRuleMutation.isPending}>
              {wecomRuleMutation.isPending ? "保存中..." : "保存"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={userDialogOpen} onOpenChange={setUserDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingUser ? "编辑用户" : "新增用户"}</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>工号</Label>
              <Input value={userForm.username} disabled={!!editingUser} onChange={(e) => setUserForm((prev) => ({ ...prev, username: e.target.value }))} />
            </div>
            <div>
              <Label>姓名</Label>
              <Input value={userForm.real_name} onChange={(e) => setUserForm((prev) => ({ ...prev, real_name: e.target.value }))} />
            </div>
            <div>
              <Label>邮箱</Label>
              <Input value={userForm.email} onChange={(e) => setUserForm((prev) => ({ ...prev, email: e.target.value }))} />
            </div>
            <div>
              <Label>电话</Label>
              <Input value={userForm.phone} onChange={(e) => setUserForm((prev) => ({ ...prev, phone: e.target.value }))} />
            </div>
            <div>
              <Label>密码</Label>
              <Input type="password" placeholder={editingUser ? "不填则保持不变" : ""} value={userForm.password} onChange={(e) => setUserForm((prev) => ({ ...prev, password: e.target.value }))} />
            </div>
            <div>
              <Label>员工编号</Label>
              <Input value={userForm.employee_no} onChange={(e) => setUserForm((prev) => ({ ...prev, employee_no: e.target.value }))} />
            </div>
            <div>
              <Label>默认门店</Label>
              <Select value={userForm.default_store_id || "none"} onValueChange={(value) => setUserForm((prev) => ({ ...prev, default_store_id: value === "none" ? "" : value }))}>
                <SelectTrigger><SelectValue placeholder="选择门店" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">未设置</SelectItem>
                  {stores.map((store) => <SelectItem key={store.storeId} value={String(store.storeId)}>{store.storeName}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>状态</Label>
              <Select value={userForm.status} onValueChange={(value) => setUserForm((prev) => ({ ...prev, status: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVE">ACTIVE</SelectItem>
                  <SelectItem value="PENDING">PENDING</SelectItem>
                  <SelectItem value="DISABLED">DISABLED</SelectItem>
                  <SelectItem value="LOCKED">LOCKED</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>角色分配</Label>
            <div className="grid grid-cols-2 gap-2 border rounded-md p-3 max-h-48 overflow-y-auto">
              {roles.map((role) => (
                <label key={role.id} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={userForm.role_ids.includes(role.id)}
                    onCheckedChange={(checked) => setUserForm((prev) => ({
                      ...prev,
                      role_ids: checked
                        ? [...prev.role_ids, role.id]
                        : prev.role_ids.filter((id) => id !== role.id),
                    }))}
                  />
                  <span>{role.role_name}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>部门归属</Label>
              <Button variant="outline" size="sm" onClick={() => setUserForm((prev) => ({
                ...prev,
                department_assignments: [...prev.department_assignments, { store_id: "", department_id: "", post_id: "", is_primary: prev.department_assignments.length === 0 }],
              }))}>新增归属</Button>
            </div>
            <div className="space-y-3">
              {userForm.department_assignments.map((assignment, index) => {
                const filteredDepartments = departments.filter((item) => String(item.store_id) === assignment.store_id);
                return (
                  <div key={`${index}-${assignment.department_id}`} className="grid grid-cols-12 gap-2 items-end border rounded-md p-3">
                    <div className="col-span-3">
                      <Label>门店</Label>
                      <Select value={assignment.store_id || "none"} onValueChange={(value) => setUserForm((prev) => ({
                        ...prev,
                        department_assignments: prev.department_assignments.map((item, itemIndex) => itemIndex === index ? { ...item, store_id: value === "none" ? "" : value, department_id: "" } : item),
                      }))}>
                        <SelectTrigger><SelectValue placeholder="门店" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">选择门店</SelectItem>
                          {stores.map((store) => <SelectItem key={store.storeId} value={String(store.storeId)}>{store.storeName}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="col-span-4">
                      <Label>部门</Label>
                      <Select value={assignment.department_id || "none"} onValueChange={(value) => setUserForm((prev) => ({
                        ...prev,
                        department_assignments: prev.department_assignments.map((item, itemIndex) => itemIndex === index ? { ...item, department_id: value === "none" ? "" : value } : item),
                      }))}>
                        <SelectTrigger><SelectValue placeholder="部门" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">选择部门</SelectItem>
                          {filteredDepartments.map((department) => <SelectItem key={department.id} value={String(department.id)}>{department.dept_name}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="col-span-3">
                      <Label>岗位</Label>
                      <Select value={assignment.post_id || "none"} onValueChange={(value) => setUserForm((prev) => ({
                        ...prev,
                        department_assignments: prev.department_assignments.map((item, itemIndex) => itemIndex === index ? { ...item, post_id: value === "none" ? "" : value } : item),
                      }))}>
                        <SelectTrigger><SelectValue placeholder="岗位" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">未设置</SelectItem>
                          {posts.map((post) => <SelectItem key={post.id} value={String(post.id)}>{post.post_name}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="col-span-1 flex justify-center pb-2">
                      <Checkbox
                        checked={assignment.is_primary}
                        onCheckedChange={(checked) => setUserForm((prev) => ({
                          ...prev,
                          department_assignments: prev.department_assignments.map((item, itemIndex) => ({
                            ...item,
                            is_primary: itemIndex === index ? !!checked : false,
                          })),
                        }))}
                      />
                    </div>
                    <div className="col-span-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={userForm.department_assignments.length === 1}
                        onClick={() => setUserForm((prev) => ({
                          ...prev,
                          department_assignments: prev.department_assignments.filter((_, itemIndex) => itemIndex !== index),
                        }))}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setUserDialogOpen(false)}>取消</Button>
            <Button onClick={() => userMutation.mutate()} disabled={userMutation.isPending}>{userMutation.isPending ? "保存中..." : "保存"}</Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingRole ? "编辑角色" : "新增角色"}</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>角色编码</Label>
              <Input value={roleForm.role_code} onChange={(e) => setRoleForm((prev) => ({ ...prev, role_code: e.target.value }))} />
            </div>
            <div>
              <Label>角色名称</Label>
              <Input value={roleForm.role_name} onChange={(e) => setRoleForm((prev) => ({ ...prev, role_name: e.target.value }))} />
            </div>
            <div>
              <Label>角色级别</Label>
              <Input value={roleForm.role_level} onChange={(e) => setRoleForm((prev) => ({ ...prev, role_level: e.target.value }))} />
            </div>
            <div className="flex items-center gap-6 pt-6">
              <label className="flex items-center gap-2 text-sm">
                <Checkbox checked={roleForm.is_system} onCheckedChange={(checked) => setRoleForm((prev) => ({ ...prev, is_system: !!checked }))} />
                系统内置
              </label>
              <label className="flex items-center gap-2 text-sm">
                <Checkbox checked={roleForm.is_active} onCheckedChange={(checked) => setRoleForm((prev) => ({ ...prev, is_active: !!checked }))} />
                启用
              </label>
            </div>
          </div>
          <div className="space-y-3">
            <Label>权限分配</Label>
            <div className="space-y-4 max-h-[420px] overflow-y-auto border rounded-md p-4">
              {permissionGroups.map(([moduleCode, items]) => (
                <div key={moduleCode}>
                  <div className="font-medium mb-2 text-sm text-slate-700">
                    {PERMISSION_MODULE_LABELS[moduleCode] || moduleCode}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {items.map((permission) => (
                      <label key={permission.id} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={roleForm.permission_ids.includes(permission.id)}
                          onCheckedChange={(checked) => setRoleForm((prev) => ({
                            ...prev,
                            permission_ids: checked
                              ? [...prev.permission_ids, permission.id]
                              : prev.permission_ids.filter((id) => id !== permission.id),
                          }))}
                        />
                        <span>{permission.permission_name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setRoleDialogOpen(false)}>取消</Button>
            <Button onClick={() => roleMutation.mutate()} disabled={roleMutation.isPending}>{roleMutation.isPending ? "保存中..." : "保存"}</Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={departmentDialogOpen} onOpenChange={setDepartmentDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>{editingDepartment ? "编辑部门" : "新增部门"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>所属门店</Label>
              <Select value={departmentForm.store_id || "none"} onValueChange={(value) => setDepartmentForm((prev) => ({ ...prev, store_id: value === "none" ? "" : value }))}>
                <SelectTrigger><SelectValue placeholder="选择门店" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">选择门店</SelectItem>
                  {stores.map((store) => <SelectItem key={store.storeId} value={String(store.storeId)}>{store.storeName}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>部门编码</Label>
              <Input value={departmentForm.dept_code} onChange={(e) => setDepartmentForm((prev) => ({ ...prev, dept_code: e.target.value }))} />
            </div>
            <div>
              <Label>部门名称</Label>
              <Input value={departmentForm.dept_name} onChange={(e) => setDepartmentForm((prev) => ({ ...prev, dept_name: e.target.value }))} />
            </div>
            <div>
              <Label>主管</Label>
              <Select value={departmentForm.manager_user_id || "none"} onValueChange={(value) => setDepartmentForm((prev) => ({ ...prev, manager_user_id: value === "none" ? "" : value }))}>
                <SelectTrigger><SelectValue placeholder="选择主管" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">未设置</SelectItem>
                  {users.map((user) => <SelectItem key={user.user_id} value={String(user.user_id)}>{user.real_name || user.username}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox checked={departmentForm.is_active} onCheckedChange={(checked) => setDepartmentForm((prev) => ({ ...prev, is_active: !!checked }))} />
              启用
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDepartmentDialogOpen(false)}>取消</Button>
            <Button onClick={() => departmentMutation.mutate()} disabled={departmentMutation.isPending}>{departmentMutation.isPending ? "保存中..." : "保存"}</Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={policyDialogOpen} onOpenChange={setPolicyDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingPolicy ? "编辑数据策略" : "新增数据策略"}</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>授权主体类型</Label>
              <Select value={policyForm.subject_type} onValueChange={(value) => setPolicyForm((prev) => ({ ...prev, subject_type: value, subject_id: "" }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {meta?.subject_types.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>授权主体</Label>
              <Select value={policyForm.subject_id || "none"} onValueChange={(value) => setPolicyForm((prev) => ({ ...prev, subject_id: value === "none" ? "" : value }))}>
                <SelectTrigger><SelectValue placeholder="选择主体" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">选择主体</SelectItem>
                  {currentSubjectOptions.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>资源</Label>
              <Select value={policyForm.resource_code} onValueChange={(value) => setPolicyForm((prev) => ({ ...prev, resource_code: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {meta?.resource_codes.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>动作</Label>
              <Select value={policyForm.action_code} onValueChange={(value) => setPolicyForm((prev) => ({ ...prev, action_code: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {meta?.action_codes.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>范围模式</Label>
              <Select value={policyForm.scope_mode} onValueChange={(value) => setPolicyForm((prev) => ({ ...prev, scope_mode: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {meta?.scope_modes.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>生效方式</Label>
              <Select value={policyForm.effect} onValueChange={(value) => setPolicyForm((prev) => ({ ...prev, effect: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {meta?.effects.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>来源类型</Label>
              <Select value={policyForm.source_type} onValueChange={(value) => setPolicyForm((prev) => ({ ...prev, source_type: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="MANUAL">MANUAL</SelectItem>
                  <SelectItem value="ERP">ERP</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>来源系统</Label>
              <Input value={policyForm.source_system} onChange={(e) => setPolicyForm((prev) => ({ ...prev, source_system: e.target.value }))} />
            </div>
            <div>
              <Label>优先级</Label>
              <Input value={policyForm.priority} onChange={(e) => setPolicyForm((prev) => ({ ...prev, priority: e.target.value }))} />
            </div>
            <div>
              <Label>外部范围 ID</Label>
              <Input value={policyForm.external_scope_id} onChange={(e) => setPolicyForm((prev) => ({ ...prev, external_scope_id: e.target.value }))} />
            </div>
            <div>
              <Label>外部范围名称</Label>
              <Input value={policyForm.external_scope_name} onChange={(e) => setPolicyForm((prev) => ({ ...prev, external_scope_name: e.target.value }))} />
            </div>
            <div className="flex items-center gap-2 pt-6">
              <Checkbox checked={policyForm.is_active} onCheckedChange={(checked) => setPolicyForm((prev) => ({ ...prev, is_active: !!checked }))} />
              <span className="text-sm">启用策略</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>门店范围</Label>
              <Textarea rows={3} placeholder="例如 601, 603" value={policyForm.store_values} onChange={(e) => setPolicyForm((prev) => ({ ...prev, store_values: e.target.value }))} />
            </div>
            <div>
              <Label>部门范围</Label>
              <Textarea rows={3} placeholder="例如 D001, 女装部" value={policyForm.department_values} onChange={(e) => setPolicyForm((prev) => ({ ...prev, department_values: e.target.value }))} />
            </div>
            <div>
              <Label>柜组范围</Label>
              <Textarea rows={3} placeholder="例如 G001, G002" value={policyForm.group_values} onChange={(e) => setPolicyForm((prev) => ({ ...prev, group_values: e.target.value }))} />
            </div>
            <div>
              <Label>楼层范围</Label>
              <Textarea rows={3} placeholder="例如 1F, B1" value={policyForm.floor_values} onChange={(e) => setPolicyForm((prev) => ({ ...prev, floor_values: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <Label>经营单元范围</Label>
              <Textarea rows={3} placeholder="例如 A101, B203" value={policyForm.unit_values} onChange={(e) => setPolicyForm((prev) => ({ ...prev, unit_values: e.target.value }))} />
            </div>
            <div>
              <Label>供应商范围</Label>
              <Textarea rows={3} placeholder="例如 S001, S002" value={policyForm.supplier_values} onChange={(e) => setPolicyForm((prev) => ({ ...prev, supplier_values: e.target.value }))} />
            </div>
            <div>
              <Label>品牌范围</Label>
              <Textarea rows={3} placeholder="例如 品牌A, 品牌B" value={policyForm.brand_values} onChange={(e) => setPolicyForm((prev) => ({ ...prev, brand_values: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <Label>品类范围</Label>
              <Textarea rows={3} placeholder="例如 女装, 鞋包" value={policyForm.category_values} onChange={(e) => setPolicyForm((prev) => ({ ...prev, category_values: e.target.value }))} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setPolicyDialogOpen(false)}>取消</Button>
            <Button onClick={() => policyMutation.mutate()} disabled={policyMutation.isPending}>{policyMutation.isPending ? "保存中..." : "保存"}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
