import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Building2, Plus, Edit, Trash2, Search, MapPin, Users } from "lucide-react";
import { insertCounterSchema, type Counter, type InsertCounter } from "@shared/schema";
import { apiRequest } from "@/lib/queryClient";

interface CountersPageProps {
  selectedStoreId?: number;
}

export default function CountersPage({ selectedStoreId }: CountersPageProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDepartment, setSelectedDepartment] = useState<string>("all");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingCounter, setEditingCounter] = useState<Counter | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Query for counters
  const { data: counters = [], isLoading } = useQuery<Counter[]>({
    queryKey: ["/api/counters", selectedStoreId],
    queryFn: async () => {
      const response = await fetch(`/api/counters${selectedStoreId ? `?storeId=${selectedStoreId}` : ""}`);
      if (!response.ok) throw new Error("Failed to fetch counters");
      return response.json();
    },
  });

  // Form setup
  const form = useForm<InsertCounter>({
    resolver: zodResolver(insertCounterSchema),
    defaultValues: {
      storeId: selectedStoreId || 1,
      counterNumber: "",
      department: "",
      building: "",
      floor: "",
      area: "0",
      status: "vacant",
      monthlyRent: undefined,
      tenantId: undefined,
      description: "",
      isActive: true,
    },
  });

  // Create counter mutation
  const createCounterMutation = useMutation({
    mutationFn: async (data: InsertCounter) => {
      const response = await fetch("/api/counters", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error("Failed to create counter");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/counters"] });
      setIsCreateDialogOpen(false);
      form.reset();
      toast({
        title: "成功",
        description: "柜位创建成功",
      });
    },
    onError: () => {
      toast({
        title: "错误",
        description: "创建柜位失败",
        variant: "destructive",
      });
    },
  });

  // Update counter mutation
  const updateCounterMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<InsertCounter> }) => {
      const response = await fetch(`/api/counters/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error("Failed to update counter");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/counters"] });
      setEditingCounter(null);
      form.reset();
      toast({
        title: "成功",
        description: "柜位更新成功",
      });
    },
    onError: () => {
      toast({
        title: "错误",
        description: "更新柜位失败",
        variant: "destructive",
      });
    },
  });

  // Delete counter mutation
  const deleteCounterMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`/api/counters/${id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to delete counter");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/counters"] });
      toast({
        title: "成功",
        description: "柜位删除成功",
      });
    },
    onError: () => {
      toast({
        title: "错误",
        description: "删除柜位失败",
        variant: "destructive",
      });
    },
  });

  // Form submit handler
  const onSubmit = (data: InsertCounter) => {
    if (editingCounter) {
      updateCounterMutation.mutate({ id: editingCounter.counterId, data });
    } else {
      createCounterMutation.mutate(data);
    }
  };

  // Start editing
  const startEdit = (counter: Counter) => {
    setEditingCounter(counter);
    form.reset({
      storeId: counter.storeId,
      counterNumber: counter.counterNumber,
      department: counter.department,
      building: counter.building,
      floor: counter.floor,
      area: counter.area.toString(),
      status: counter.status,
      monthlyRent: counter.monthlyRent?.toString(),
      tenantId: counter.tenantId || undefined,
      description: counter.description || "",
      isActive: counter.isActive,
    });
  };

  // Cancel editing
  const cancelEdit = () => {
    setEditingCounter(null);
    form.reset();
  };

  // Filter counters
  const filteredCounters = counters.filter((counter: Counter) => {
    const matchesSearch = 
      counter.counterNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      counter.department.toLowerCase().includes(searchTerm.toLowerCase()) ||
      counter.building.toLowerCase().includes(searchTerm.toLowerCase()) ||
      counter.floor.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesDepartment = selectedDepartment === "all" || counter.department === selectedDepartment;
    
    return matchesSearch && matchesDepartment;
  });

  // Get unique departments for filter
  const departments = Array.from(new Set(counters.map((c) => c.department).filter(dept => dept && dept.trim() !== "")));

  // Status color mapping
  const getStatusColor = (status: string) => {
    switch (status) {
      case "occupied": return "bg-green-100 text-green-800";
      case "vacant": return "bg-blue-100 text-blue-800";
      case "maintenance": return "bg-yellow-100 text-yellow-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  // Status text mapping
  const getStatusText = (status: string) => {
    switch (status) {
      case "occupied": return "已租用";
      case "vacant": return "空置";
      case "maintenance": return "维护中";
      default: return status;
    }
  };

  return (
    <div className="p-6" data-testid="counters-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900" data-testid="text-page-title">柜位管理</h1>
          <p className="text-slate-600 mt-1">管理商场柜位信息，包括柜位号、部门、楼栋、楼层等基础信息</p>
        </div>
        <Dialog open={isCreateDialogOpen || !!editingCounter} onOpenChange={(open) => {
          if (!open) {
            setIsCreateDialogOpen(false);
            cancelEdit();
          }
        }}>
          <DialogTrigger asChild>
            <Button 
              onClick={() => setIsCreateDialogOpen(true)}
              data-testid="button-create-counter"
            >
              <Plus className="w-4 h-4 mr-2" />
              新增柜位
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md" data-testid="dialog-counter-form">
            <DialogHeader>
              <DialogTitle>
                {editingCounter ? "编辑柜位" : "新增柜位"}
              </DialogTitle>
            </DialogHeader>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="counterNumber"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>柜位号</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="如：A001" data-testid="input-counter-number" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="department"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>部门</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="如：服装部" data-testid="input-department" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="building"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>楼栋</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="如：A栋" data-testid="input-building" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="floor"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>楼层</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="如：1F" data-testid="input-floor" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="area"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>面积 (平方米)</FormLabel>
                        <FormControl>
                          <Input {...field} type="number" step="0.01" data-testid="input-area" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="status"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>状态</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger data-testid="select-status">
                              <SelectValue placeholder="选择状态" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="vacant">空置</SelectItem>
                            <SelectItem value="occupied">已租用</SelectItem>
                            <SelectItem value="maintenance">维护中</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={form.control}
                  name="monthlyRent"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>月租金 (元)</FormLabel>
                      <FormControl>
                        <Input {...field} type="number" step="0.01" value={field.value || ""} data-testid="input-monthly-rent" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>备注</FormLabel>
                      <FormControl>
                        <Textarea {...field} placeholder="备注信息" value={field.value || ""} data-testid="textarea-description" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="flex gap-2 pt-4">
                  <Button 
                    type="submit" 
                    disabled={createCounterMutation.isPending || updateCounterMutation.isPending}
                    data-testid="button-submit-counter"
                  >
                    {editingCounter ? "更新" : "创建"}
                  </Button>
                  <Button 
                    type="button" 
                    variant="outline" 
                    onClick={cancelEdit}
                    data-testid="button-cancel-counter"
                  >
                    取消
                  </Button>
                </div>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search and Filter */}
      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
          <Input
            placeholder="搜索柜位号、部门、楼栋、楼层..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
            data-testid="input-search-counters"
          />
        </div>
        <Select value={selectedDepartment} onValueChange={setSelectedDepartment}>
          <SelectTrigger className="w-48" data-testid="select-department-filter">
            <SelectValue placeholder="按部门筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部部门</SelectItem>
            {departments.map((dept) => (
              <SelectItem key={dept} value={dept}>{dept}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <Building2 className="w-8 h-8 text-blue-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-slate-600">总柜位数</p>
                <p className="text-2xl font-bold text-slate-900" data-testid="text-total-counters">
                  {counters.length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <Users className="w-8 h-8 text-green-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-slate-600">已租用</p>
                <p className="text-2xl font-bold text-slate-900" data-testid="text-occupied-counters">
                  {counters.filter((c) => c.status === "occupied").length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <MapPin className="w-8 h-8 text-orange-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-slate-600">空置</p>
                <p className="text-2xl font-bold text-slate-900" data-testid="text-vacant-counters">
                  {counters.filter((c) => c.status === "vacant").length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <Building2 className="w-8 h-8 text-red-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-slate-600">维护中</p>
                <p className="text-2xl font-bold text-slate-900" data-testid="text-maintenance-counters">
                  {counters.filter((c) => c.status === "maintenance").length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Counters Table */}
      <div className="bg-white rounded-lg border border-slate-200">
        {isLoading ? (
          <div className="text-center py-8">
            <p className="text-slate-600">加载中...</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>柜位号</TableHead>
                <TableHead>部门</TableHead>
                <TableHead>位置</TableHead>
                <TableHead>面积</TableHead>
                <TableHead>月租金</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>描述</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCounters.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-slate-500">
                    暂无柜位数据
                  </TableCell>
                </TableRow>
              ) : (
                filteredCounters.map((counter) => (
                  <TableRow key={counter.counterId} data-testid={`row-counter-${counter.counterId}`}>
                    <TableCell className="font-medium">{counter.counterNumber}</TableCell>
                    <TableCell>{counter.department}</TableCell>
                    <TableCell>{counter.building} - {counter.floor}</TableCell>
                    <TableCell>{counter.area} m²</TableCell>
                    <TableCell>
                      {counter.monthlyRent ? `¥${parseFloat(counter.monthlyRent).toLocaleString()}` : '-'}
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(counter.status)}>
                        {getStatusText(counter.status)}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <div className="truncate" title={counter.description || ''}>
                        {counter.description || '-'}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={() => startEdit(counter)}
                          data-testid={`button-edit-${counter.counterId}`}
                        >
                          <Edit className="w-3 h-3 mr-1" />
                          编辑
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={() => deleteCounterMutation.mutate(counter.counterId)}
                          disabled={deleteCounterMutation.isPending}
                          data-testid={`button-delete-${counter.counterId}`}
                        >
                          <Trash2 className="w-3 h-3 mr-1" />
                          删除
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}