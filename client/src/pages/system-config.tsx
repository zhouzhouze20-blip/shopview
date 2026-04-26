import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api";
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
import { Plus, Shield, Users, Building2, Filter } from "lucide-react";

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
  items: DataPolicyItem[];
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

interface SystemConfigPageProps {
  initialTab?: "users" | "roles" | "departments" | "policies";
}

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
  resource_code: "counter",
  action_code: "view",
  scope_mode: "CUSTOM",
  effect: "ALLOW",
  priority: "100",
  is_active: true,
  store_values: "",
  department_values: "",
  group_values: "",
  floor_values: "",
  unit_values: "",
};

const splitValues = (value: string) =>
  value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);

const buildPolicyItems = (form: typeof emptyPolicyForm): DataPolicyItem[] => {
  const groups: Array<[string, string[]]> = [
    ["store", splitValues(form.store_values)],
    ["department", splitValues(form.department_values)],
    ["group", splitValues(form.group_values)],
    ["floor", splitValues(form.floor_values)],
    ["unit", splitValues(form.unit_values)],
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
  const [tab, setTab] = useState<SystemConfigPageProps["initialTab"]>(initialTab);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [departmentDialogOpen, setDepartmentDialogOpen] = useState(false);
  const [policyDialogOpen, setPolicyDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [editingRole, setEditingRole] = useState<RoleItem | null>(null);
  const [editingDepartment, setEditingDepartment] = useState<DepartmentItem | null>(null);
  const [editingPolicy, setEditingPolicy] = useState<DataPolicy | null>(null);
  const [userForm, setUserForm] = useState(emptyUserForm);
  const [roleForm, setRoleForm] = useState(emptyRoleForm);
  const [departmentForm, setDepartmentForm] = useState(emptyDepartmentForm);
  const [policyForm, setPolicyForm] = useState(emptyPolicyForm);

  const queryClient = useQueryClient();
  const { toast } = useToast();

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab]);

  const { data: stores = [] } = useQuery<StoreOption[]>({
    queryKey: ["/api/stores"],
    queryFn: async () => {
      const data = await apiGet<any[]>("/api/stores");
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

  const { data: meta } = useQuery<SystemMeta>({
    queryKey: ["/api/system/meta"],
    queryFn: () => apiGet<SystemMeta>("/api/system/meta"),
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

  const invalidateSystemQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["/api/system/users"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/roles"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/departments"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/data-policies"] }),
      queryClient.invalidateQueries({ queryKey: ["/api/system/meta"] }),
    ]);
  };

  const userMutation = useMutation({
    mutationFn: async () => {
      if (!userForm.username.trim()) throw new Error("请输入用户名");
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
    });
    setPolicyDialogOpen(true);
  };

  const currentSubjectOptions = policyForm.subject_type === "ROLE" ? meta?.roles ?? [] : meta?.users ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">系统配置中心</h1>
          <p className="text-slate-600 mt-1">统一维护账号、角色、组织和数据范围策略。</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
      </div>

      <Tabs value={tab} onValueChange={(value) => setTab(value as SystemConfigPageProps["initialTab"])}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="users">用户</TabsTrigger>
          <TabsTrigger value="roles">角色</TabsTrigger>
          <TabsTrigger value="departments">部门</TabsTrigger>
          <TabsTrigger value="policies">数据策略</TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreateUser}><Plus className="mr-2 h-4 w-4" />新增用户</Button>
          </div>
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>用户名</TableHead>
                    <TableHead>姓名</TableHead>
                    <TableHead>角色</TableHead>
                    <TableHead>默认门店</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
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
          <div className="flex justify-end">
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
      </Tabs>

      <Dialog open={userDialogOpen} onOpenChange={setUserDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingUser ? "编辑用户" : "新增用户"}</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>用户名</Label>
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
                  <div className="font-medium mb-2 uppercase text-sm text-slate-700">{moduleCode}</div>
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
              <Label>优先级</Label>
              <Input value={policyForm.priority} onChange={(e) => setPolicyForm((prev) => ({ ...prev, priority: e.target.value }))} />
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
