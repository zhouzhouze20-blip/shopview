import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DataScopeUserEditor } from "@/components/data-scope-user-editor"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getAdminDataScopes, getAdminUsers } from "@/lib/admin-data"

export default async function DataScopeManagementPage() {
  const [scopes, users] = await Promise.all([
    getAdminDataScopes(),
    getAdminUsers(),
  ])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">数据范围管理</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          配置用户可以查看的门店、事业部或全部数据范围。
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-medium">数据范围</CardTitle>
          <Badge variant="secondary">{scopes.length} 个范围</Badge>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>范围编码</TableHead>
                  <TableHead>范围名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>门店编码</TableHead>
                  <TableHead>门店名称</TableHead>
                  <TableHead>用户数</TableHead>
                  <TableHead className="w-28 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {scopes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                      暂无数据范围，请先执行 docs/auth-permission-schema.sql 建表。
                    </TableCell>
                  </TableRow>
                ) : (
                  scopes.map((scope) => (
                    <TableRow key={scope.id}>
                      <TableCell className="font-medium">{scope.scopeCode}</TableCell>
                      <TableCell>{scope.scopeName}</TableCell>
                      <TableCell>{scope.scopeType}</TableCell>
                      <TableCell className="max-w-64 truncate" title={scope.storeIds}>
                        {scope.storeIds}
                      </TableCell>
                      <TableCell className="max-w-96 truncate" title={scope.storeNames}>
                        {scope.storeNames}
                      </TableCell>
                      <TableCell>{scope.userCount}</TableCell>
                      <TableCell className="text-right">
                        <DataScopeUserEditor scope={scope} users={users} />
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
