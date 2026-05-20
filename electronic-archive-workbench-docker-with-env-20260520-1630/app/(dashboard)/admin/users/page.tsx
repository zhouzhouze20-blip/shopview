import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { UserRoleEditor } from "@/components/user-role-editor"
import { UserStoreScopeEditor } from "@/components/user-store-scope-editor"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { SyncWecomUsersButton } from "@/components/sync-wecom-users-button"
import { getAdminRoles, getAdminUsers } from "@/lib/admin-data"
import { getPaymentStores } from "@/lib/stores"

export default async function UserManagementPage() {
  const [users, roles, stores] = await Promise.all([
    getAdminUsers(),
    getAdminRoles(),
    getPaymentStores(),
  ])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">用户管理</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          管理系统用户、企微账号绑定、角色和数据范围。
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-medium">用户列表</CardTitle>
          <div className="flex items-center gap-3">
            <Badge variant="secondary">{users.length} 个用户</Badge>
            <SyncWecomUsersButton />
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用户名</TableHead>
                  <TableHead>姓名</TableHead>
                  <TableHead>企微 UserID</TableHead>
                  <TableHead>手机号</TableHead>
                  <TableHead>部门</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>数据范围</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>最后登录</TableHead>
                  <TableHead className="w-52 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="h-24 text-center text-muted-foreground">
                      暂无用户数据，请先执行 docs/auth-permission-schema.sql 建表。
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">{user.username}</TableCell>
                      <TableCell title={user.displayName}>{user.displayName}</TableCell>
                      <TableCell title={user.wecomUserId}>{user.wecomUserId}</TableCell>
                      <TableCell>{user.mobile}</TableCell>
                      <TableCell title={user.departmentName}>{user.departmentName}</TableCell>
                      <TableCell className="max-w-56 truncate" title={user.roleNames}>
                        {user.roleNames}
                      </TableCell>
                      <TableCell className="max-w-56 truncate" title={user.dataScopeNames}>
                        {user.dataScopeNames}
                      </TableCell>
                      <TableCell>
                        <Badge variant={user.status === "enabled" ? "default" : "outline"}>
                          {user.status === "enabled" ? "启用" : "停用"}
                        </Badge>
                      </TableCell>
                      <TableCell>{user.lastLoginTime}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <UserRoleEditor user={user} roles={roles} />
                          <UserStoreScopeEditor user={user} stores={stores} />
                        </div>
                      </TableCell>
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
