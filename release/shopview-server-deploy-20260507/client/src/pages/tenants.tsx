import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Search, Building2, Phone, Mail, MapPin } from "lucide-react";
import { Tenant } from "@/lib/schema";
import { useStore } from "@/contexts/StoreContext";
import GlobalStoreSelector from "@/components/global-store-selector";
import { apiGet } from "@/lib/api";

interface TenantsPageProps {
  selectedStoreId?: number;
}

export default function TenantsPage({ selectedStoreId }: TenantsPageProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const { getCurrentFilter } = useStore();

  // 使用全局门店筛选
  const currentFilter = getCurrentFilter();
  const effectiveStoreId = selectedStoreId || currentFilter.storeId;

  const mapTenant = (tenant: any): Tenant => ({
    tenantId: tenant.tenant_id,
    companyName: tenant.company_name,
    tenantCode: tenant.tenant_code,
    legalRepresentative: tenant.legal_representative ?? undefined,
    contactPerson: tenant.contact_person ?? undefined,
    contactPhone: tenant.contact_phone ?? undefined,
    contactEmail: tenant.contact_email ?? undefined,
    address: tenant.address ?? undefined,
    businessCategory: tenant.business_category ?? undefined,
    isActive: tenant.is_active,
    createdAt: tenant.created_at,
    updatedAt: tenant.updated_at ?? undefined,
  });

  const { data: tenants, isLoading } = useQuery<Tenant[]>({
    queryKey: effectiveStoreId ? ["/api/tenants/", effectiveStoreId] : ["/api/tenants/"],
    queryFn: async () => {
      const query = effectiveStoreId ? `?storeId=${encodeURIComponent(String(effectiveStoreId))}` : "";
      const data = await apiGet<any[]>(`/api/tenants/${query}`);
      return data.map(mapTenant);
    },
  });

  const { data: searchResults, isLoading: searchLoading } = useQuery<Tenant[]>({
    queryKey: ["/api/tenants/search/", searchQuery, effectiveStoreId],
    queryFn: async () => {
      const params = new URLSearchParams({ keyword: searchQuery });
      if (effectiveStoreId) params.set('storeId', effectiveStoreId.toString());
      const data = await apiGet<any[]>(`/api/tenants/search/?${params.toString()}`);
      return data.map(mapTenant);
    },
    enabled: searchQuery.length > 0,
  });

  const displayTenants = searchQuery ? searchResults : tenants;

  const formatDate = (dateString: string | Date | null) => {
    if (!dateString) return '未设置';
    const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
    return date.toLocaleDateString('zh-CN');
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="tenants-page">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900" data-testid="text-page-title">
              商户管理
            </h1>
            <p className="text-slate-600 mt-1">
              管理所有商户的基本信息和合作状态
            </p>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700" data-testid="button-add-tenant">
            <Plus className="w-4 h-4 mr-2" />
            新增商户
          </Button>
        </div>

        {/* 全局门店选择器 */}
        <GlobalStoreSelector className="mb-6" />

        {/* 搜索栏 */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
            <input
              type="text"
              placeholder="搜索商户名称、编码或联系人..."
              className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              data-testid="input-search-tenants"
            />
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总商户数</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold" data-testid="text-total-tenants">
                {isLoading ? <Skeleton className="h-8 w-16" /> : tenants?.length || 0}
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">活跃商户</CardTitle>
              <Building2 className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600" data-testid="text-active-tenants">
                {isLoading ? <Skeleton className="h-8 w-16" /> : (tenants?.filter((t: Tenant) => t.isActive).length || 0)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">停用商户</CardTitle>
              <Building2 className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-600" data-testid="text-inactive-tenants">
                {isLoading ? <Skeleton className="h-8 w-16" /> : (tenants?.filter((t: Tenant) => !t.isActive).length || 0)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">本月新增</CardTitle>
              <Plus className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600" data-testid="text-new-tenants">
                {isLoading ? <Skeleton className="h-8 w-16" /> : "0"}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 商户列表 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {isLoading || searchLoading ? (
            Array.from({ length: 6 }).map((_, index) => (
              <Card key={index}>
                <CardHeader>
                  <Skeleton className="h-6 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                </CardContent>
              </Card>
            ))
          ) : displayTenants && displayTenants.length > 0 ? (
            displayTenants.map((tenant: Tenant) => (
              <Card key={tenant.tenantId} className="hover:shadow-lg transition-shadow cursor-pointer" data-testid={`tenant-card-${tenant.tenantId}`}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg" data-testid={`text-tenant-name-${tenant.tenantId}`}>
                      {tenant.companyName}
                    </CardTitle>
                    <Badge 
                      variant={tenant.isActive ? "default" : "secondary"}
                      className={tenant.isActive ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-800"}
                      data-testid={`badge-tenant-status-${tenant.tenantId}`}
                    >
                      {tenant.isActive ? "活跃" : "停用"}
                    </Badge>
                  </div>
                  <p className="text-sm text-slate-600" data-testid={`text-tenant-code-${tenant.tenantId}`}>
                    编码: {tenant.tenantCode}
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {tenant.legalRepresentative && (
                      <div className="flex items-center text-sm text-slate-600">
                        <Building2 className="w-4 h-4 mr-2" />
                        <span>法人: {tenant.legalRepresentative}</span>
                      </div>
                    )}
                    
                    {tenant.contactPerson && (
                      <div className="flex items-center text-sm text-slate-600">
                        <Phone className="w-4 h-4 mr-2" />
                        <span>{tenant.contactPerson}</span>
                        {tenant.contactPhone && (
                          <span className="ml-2">({tenant.contactPhone})</span>
                        )}
                      </div>
                    )}
                    
                    {tenant.contactEmail && (
                      <div className="flex items-center text-sm text-slate-600">
                        <Mail className="w-4 h-4 mr-2" />
                        <span>{tenant.contactEmail}</span>
                      </div>
                    )}
                    
                    {tenant.address && (
                      <div className="flex items-start text-sm text-slate-600">
                        <MapPin className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                        <span className="line-clamp-2">{tenant.address}</span>
                      </div>
                    )}
                    
                    <div className="text-xs text-slate-400 pt-2 border-t">
                      创建时间: {formatDate(tenant.createdAt)}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <div className="col-span-full text-center py-12">
              <Building2 className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">
                {searchQuery ? "未找到匹配的商户" : "暂无商户"}
              </h3>
              <p className="text-slate-600 mb-4">
                {searchQuery ? "请尝试调整搜索条件" : "点击\"新增商户\"按钮开始添加商户信息"}
              </p>
              {!searchQuery && (
                <Button className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="w-4 h-4 mr-2" />
                  新增商户
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
