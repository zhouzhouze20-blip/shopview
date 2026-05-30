import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CreateRoleDialog } from "@/components/create-role-dialog"
import { RolePermissionEditor } from "@/components/role-permission-editor"
import { SyncDefaultPermissionsButton } from "@/components/sync-default-permissions-button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getAdminPermissions, getAdminRoles } from "@/lib/admin-data"

export default async function PermissionManagementPage() {
  const [roles, permissions] = await Promise.all([
    getAdminRoles(),
    getAdminPermissions(),
  ])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">权限管理</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          维护角色、菜单权限和操作权限，可按角色分配可用权限点。
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-medium">角色</CardTitle>
          <div className="flex items-center gap-2">
            <SyncDefaultPermissionsButton />
            <CreateRoleDialog permissions={permissions} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>角色编码</TableHead>
                  <TableHead>角色名称</TableHead>
                  <TableHead>用户数</TableHead>
                  <TableHead>权限</TableHead>
                  <TableHead>说明</TableHead>
                  <TableHead className="w-28 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {roles.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="h-20 text-center text-muted-foreground">
                      暂无角色数据
                    </TableCell>
                  </TableRow>
                ) : (
                  roles.map((role) => (
                    <TableRow key={role.id}>
                      <TableCell className="font-medium">{role.roleCode}</TableCell>
                      <TableCell>{role.roleName}</TableCell>
                      <TableCell>{role.userCount}</TableCell>
                      <TableCell className="max-w-96 truncate" title={role.permissionNames}>
                        {role.permissionNames}
                      </TableCell>
                      <TableCell title={role.description}>{role.description}</TableCell>
                      <TableCell className="text-right">
                        <RolePermissionEditor role={role} permissions={permissions} />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-medium">权限点</CardTitle>
          <Badge variant="secondary">{permissions.length} 个权限点</Badge>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>权限编码</TableHead>
                  <TableHead>权限名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>路由</TableHead>
                  <TableHead>上级</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {permissions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="h-20 text-center text-muted-foreground">
                      暂无权限数据
                    </TableCell>
                  </TableRow>
                ) : (
                  permissions.map((permission) => (
                    <TableRow key={permission.id}>
                      <TableCell className="font-medium">{permission.permissionCode}</TableCell>
                      <TableCell>{permission.permissionName}</TableCell>
                      <TableCell>{permission.permissionType}</TableCell>
                      <TableCell>{permission.routePath}</TableCell>
                      <TableCell>{permission.parentCode}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
