import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Edit, Trash2, Search, Building2, Users, MapPin, FileText } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { insertCounterSchema, type Counter, type InsertCounter } from "@shared/schema";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

export default function CountersPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDepartment, setSelectedDepartment] = useState("all");
  const [editingCounter, setEditingCounter] = useState<Counter | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Form setup
  const form = useForm<InsertCounter>({
    resolver: zodResolver(insertCounterSchema),
    defaultValues: {
      counterNumber: "",
      department: "",
      building: "",
      floor: "",
      area: "",
      status: "vacant",
      monthlyRent: "",
      groupCode: "",
      groupName: "",
      description: "",
    },
  });

  // Queries
  const { data: counters = [], isLoading } = useQuery<Counter[]>({
    queryKey: ['/api/counters'],
  });

  // Mutations
  const createCounterMutation = useMutation({
    mutationFn: (data: InsertCounter) => apiRequest('POST', '/api/counters', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/counters'] });
      toast({ title: "柜位创建成功", description: "新柜位已成功添加到系统中" });
      form.reset();
      setIsDialogOpen(false);
    },
    onError: (error: any) => {
      toast({ 
        title: "创建失败", 
        description: error.message || "创建柜位时发生错误",
        variant: "destructive"
      });
    },
  });

  const updateCounterMutation = useMutation({
    mutationFn: ({ counterId, data }: { counterId: number; data: Partial<InsertCounter> }) => 
      apiRequest('PUT', `/api/counters/${counterId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/counters'] });
      toast({ title: "柜位更新成功", description: "柜位信息已成功更新" });
      form.reset();
      setEditingCounter(null);
      setIsDialogOpen(false);
    },
    onError: (error: any) => {
      toast({ 
        title: "更新失败", 
        description: error.message || "更新柜位时发生错误",
        variant: "destructive"
      });
    },
  });

  const deleteCounterMutation = useMutation({
    mutationFn: (counterId: number) => apiRequest('DELETE', `/api/counters/${counterId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/counters'] });
      toast({ title: "柜位删除成功", description: "柜位已从系统中移除" });
    },
    onError: (error: any) => {
      toast({ 
        title: "删除失败", 
        description: error.message || "删除柜位时发生错误",
        variant: "destructive"
      });
    },
  });

  // Event handlers
  const onSubmit = (data: InsertCounter) => {
    if (editingCounter) {
      updateCounterMutation.mutate({ counterId: editingCounter.counterId, data });
    } else {
      createCounterMutation.mutate(data);
    }
  };

  const startEdit = (counter: Counter) => {
    setEditingCounter(counter);
    form.reset({
      counterNumber: counter.counterNumber,
      department: counter.department,
      building: counter.building,
      floor: counter.floor,
      area: counter.area,
      status: counter.status,
      monthlyRent: counter.monthlyRent || "",
      groupCode: counter.groupCode || "",
      groupName: counter.groupName || "",
      description: counter.description || "",
    });
    setIsDialogOpen(true);
  };

  const startCreate = () => {
    setEditingCounter(null);
    form.reset({
      counterNumber: "",
      department: "",
      building: "",
      floor: "",
      area: "",
      status: "vacant",
      monthlyRent: "",
      groupCode: "",
      groupName: "",
      description: "",
    });
    setIsDialogOpen(true);
  };

  const cancelEdit = () => {
    setEditingCounter(null);
    form.reset();
    setIsDialogOpen(false);
  };

  // Data processing
  const departments = Array.from(new Set(counters.map(c => c.department)));

  const filteredCounters = counters.filter(counter => {
    const matchesSearch = !searchTerm || 
      counter.counterNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      counter.department.toLowerCase().includes(searchTerm.toLowerCase()) ||
      counter.building.toLowerCase().includes(searchTerm.toLowerCase()) ||
      counter.floor.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesDepartment = selectedDepartment === "all" || counter.department === selectedDepartment;
    
    return matchesSearch && matchesDepartment;
  });

  // Status helpers
  const getStatusColor = (status: string) => {
    switch (status) {
      case "occupied": return "bg-green-100 text-green-800";
      case "vacant": return "bg-gray-100 text-gray-800";
      case "maintenance": return "bg-yellow-100 text-yellow-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "occupied": return "已租用";
      case "vacant": return "空置";
      case "maintenance": return "维护中";
      default: return status;
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-6" data-testid="counters-loading">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-lg">正在加载柜位信息...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="counters-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">柜位管理</h1>
          <p className="text-muted-foreground mt-2">
            管理门店柜位信息，分配租赁状态和收费标准
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={startCreate} data-testid="button-create-counter">
              <Plus className="w-4 h-4 mr-2" />
              新增柜位
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle data-testid="dialog-title">
                {editingCounter ? "编辑柜位" : "新增柜位"}
              </DialogTitle>
            </DialogHeader>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
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
                          <Input {...field} placeholder="如：电子产品" data-testid="input-department" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

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
                          <Input {...field} type="number" step="0.01" placeholder="如：25.5" data-testid="input-area" />
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
                        <Select onValueChange={field.onChange} value={field.value}>
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

                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="groupCode"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>柜组编码 <span className="text-xs text-gray-500">(租用时填写)</span></FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value || ""} placeholder="如：GRP001" data-testid="input-group-code" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="groupName"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>柜组名称 <span className="text-xs text-gray-500">(租用时填写)</span></FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value || ""} placeholder="如：时尚生活馆" data-testid="input-group-name" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
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
                </div>

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
      <div className="bg-white rounded-lg shadow-sm border border-slate-200">
        {filteredCounters.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-lg text-slate-500">暂无柜位数据</div>
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
                <TableHead>柜组编码</TableHead>
                <TableHead>柜组名称</TableHead>
                <TableHead>描述</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCounters.map((counter) => (
                <TableRow key={counter.counterId} data-testid={`row-counter-${counter.counterId}`}>
                  <TableCell className="font-medium">{counter.counterNumber}</TableCell>
                  <TableCell>{counter.department}</TableCell>
                  <TableCell>{counter.building}-{counter.floor}</TableCell>
                  <TableCell>{counter.area} m²</TableCell>
                  <TableCell>
                    {counter.monthlyRent ? `¥${parseFloat(counter.monthlyRent).toLocaleString()}` : '-'}
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(counter.status)}>
                      {getStatusText(counter.status)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {counter.groupCode || '-'}
                  </TableCell>
                  <TableCell>
                    {counter.groupName || '-'}
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
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}