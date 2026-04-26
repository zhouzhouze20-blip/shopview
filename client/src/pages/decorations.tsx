import { useEffect, useMemo, useState } from "react";
import {
  BadgeCheck,
  ClipboardList,
  FileUp,
  Filter,
  HardHat,
  Plus,
  RefreshCw,
  ScrollText,
  Send,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import {
  DecorationAction,
  DecorationProjectCreateInput,
  DecorationProjectDetail,
  DecorationProjectListItem,
  DecorationTodoItem,
  getMockSpaceOptions,
} from "@/lib/decorations";
import {
  useAcceptanceDecoration,
  useCancelDecoration,
  useCompletionSubmitDecoration,
  useCreateDecoration,
  useCreateDecorationAttachment,
  useDecorationDetail,
  useDecorationList,
  useDecorationMeta,
  useDecorationTimeline,
  useDecorationTodos,
  useDecorationWorkflow,
  useDeleteDecorationAttachment,
  useDepositConfirmDecoration,
  useEntryConfirmDecoration,
  useLeaderApproveDecoration,
  usePropertyReviewDecoration,
  useRefundApprovalDecoration,
  useRefundConfirmDecoration,
  useSettlementDecoration,
  useSubmitDecoration,
} from "@/hooks/useDecorations";
import { useStore } from "@/contexts/StoreContext";

type DecorationTab = "projects" | "todos";

const STATUS_BADGE_CLASS: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700 border-slate-200",
  PENDING_PROPERTY_REVIEW: "bg-amber-100 text-amber-800 border-amber-200",
  PENDING_LEADER_APPROVAL: "bg-blue-100 text-blue-800 border-blue-200",
  PENDING_DEPOSIT_CONFIRM: "bg-fuchsia-100 text-fuchsia-800 border-fuchsia-200",
  PENDING_ENTRY_CONFIRM: "bg-orange-100 text-orange-800 border-orange-200",
  IN_CONSTRUCTION: "bg-cyan-100 text-cyan-800 border-cyan-200",
  PENDING_ACCEPTANCE: "bg-violet-100 text-violet-800 border-violet-200",
  PENDING_SETTLEMENT: "bg-lime-100 text-lime-800 border-lime-200",
  PENDING_REFUND_APPROVAL: "bg-rose-100 text-rose-800 border-rose-200",
  COMPLETED: "bg-emerald-100 text-emerald-800 border-emerald-200",
  REJECTED: "bg-red-100 text-red-800 border-red-200",
  CANCELLED: "bg-neutral-100 text-neutral-700 border-neutral-200",
};

const todayString = () => new Date().toISOString().slice(0, 10);

const defaultCreateForm = (storeId?: number | null): DecorationProjectCreateInput => {
  const space = getMockSpaceOptions(storeId)[0] ?? getMockSpaceOptions()[0];
  return {
    store_id: storeId ?? space?.store_id ?? 601,
    department_id: 801,
    applicant_phone: "13800000000",
    brand_name: "",
    tenant_name: "",
    contractor_name: "",
    contractor_contact: "",
    contractor_phone: "",
    fitout_type: "REMODEL",
    fitout_reason: "",
    description: "",
    planned_entry_date: todayString(),
    planned_finish_date: todayString(),
    applied_area: space?.applied_area ?? 50,
    spaces: space
      ? [
          {
            space_type: space.space_type,
            hall_id: space.hall_id,
            business_unit_id: space.business_unit_id,
            floor_id: space.floor_id,
            space_code: space.space_code,
            space_name: space.space_name,
            applied_area: space.applied_area,
          },
        ]
      : [],
  };
};

export default function DecorationsPage({ initialTab = "projects" }: { initialTab?: DecorationTab }) {
  const { toast } = useToast();
  const { selectedStoreId } = useStore();
  const [tab, setTab] = useState<DecorationTab>(initialTab);
  const [keyword, setKeyword] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [attachmentOpen, setAttachmentOpen] = useState(false);
  const [actionOpen, setActionOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<DecorationAction | null>(null);
  const [createForm, setCreateForm] = useState<DecorationProjectCreateInput>(defaultCreateForm(selectedStoreId));
  const [attachmentForm, setAttachmentForm] = useState({
    attachment_type: "CONTRACTOR_LICENSE",
    file_name: "",
    file_url: "/uploads/mock-file.pdf",
  });
  const [actionForm, setActionForm] = useState<Record<string, string>>({});

  const metaQuery = useDecorationMeta();
  const listQuery = useDecorationList({
    store_id: selectedStoreId ?? undefined,
    keyword: keyword || undefined,
    mine: false,
  });
  const todosQuery = useDecorationTodos();
  const detailQuery = useDecorationDetail(selectedProjectId);
  const workflowQuery = useDecorationWorkflow(selectedProjectId);
  const timelineQuery = useDecorationTimeline(selectedProjectId);

  const createMutation = useCreateDecoration();
  const attachmentMutation = useCreateDecorationAttachment();
  const deleteAttachmentMutation = useDeleteDecorationAttachment();
  const submitMutation = useSubmitDecoration();
  const cancelMutation = useCancelDecoration();
  const propertyReviewMutation = usePropertyReviewDecoration();
  const leaderMutation = useLeaderApproveDecoration();
  const depositMutation = useDepositConfirmDecoration();
  const entryMutation = useEntryConfirmDecoration();
  const completionMutation = useCompletionSubmitDecoration();
  const acceptanceMutation = useAcceptanceDecoration();
  const settlementMutation = useSettlementDecoration();
  const refundApprovalMutation = useRefundApprovalDecoration();
  const refundConfirmMutation = useRefundConfirmDecoration();

  const projects = listQuery.data ?? [];
  const todos = todosQuery.data ?? [];
  const detail = detailQuery.data ?? null;

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab]);

  useEffect(() => {
    if (!selectedProjectId && projects.length > 0) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  useEffect(() => {
    setCreateForm(defaultCreateForm(selectedStoreId));
  }, [selectedStoreId]);

  const currentSpaceOptions = useMemo(
    () => getMockSpaceOptions(createForm.store_id),
    [createForm.store_id],
  );

  const detailCards = useMemo(() => {
    if (!detail) return [];
    return [
      { label: "门店", value: detail.store_name ?? `#${detail.store_id}` },
      { label: "部门", value: detail.department_name ?? `#${detail.department_id}` },
      { label: "施工单位", value: detail.contractor_name },
      { label: "施工负责人", value: `${detail.contractor_contact} / ${detail.contractor_phone}` },
      { label: "计划工期", value: `${detail.planned_entry_date} 至 ${detail.planned_finish_date}` },
      { label: "申请面积", value: `${detail.applied_area} ㎡` },
    ];
  }, [detail]);

  const mutationBusy =
    createMutation.isPending ||
    attachmentMutation.isPending ||
    deleteAttachmentMutation.isPending ||
    submitMutation.isPending ||
    cancelMutation.isPending ||
    propertyReviewMutation.isPending ||
    leaderMutation.isPending ||
    depositMutation.isPending ||
    entryMutation.isPending ||
    completionMutation.isPending ||
    acceptanceMutation.isPending ||
    settlementMutation.isPending ||
    refundApprovalMutation.isPending ||
    refundConfirmMutation.isPending;

  const openActionDialog = (action: DecorationAction) => {
    setPendingAction(action);
    setActionOpen(true);
    setActionForm({
      comment: "",
      review_result: "APPROVED",
      action: "APPROVE",
      entry_result: "APPROVED",
      acceptance_result: "APPROVED",
      received_date: todayString(),
      entry_date: todayString(),
      actual_finish_date: todayString(),
      acceptance_date: todayString(),
      refund_date: todayString(),
      measured_area: detail?.applied_area?.toString?.() ?? "50",
      actual_power_usage: "320",
      power_fee_amount: "640",
      deduction_amount: "0",
      refund_amount: detail?.refund_amount?.toString?.() ?? "9160",
      deposit_amount_expected: detail?.deposit_amount?.toString?.() ?? "10000",
      deposit_amount_received: detail?.deposit_amount?.toString?.() ?? "10000",
      approved_refund_amount: detail?.refund_amount?.toString?.() ?? "9160",
      final_refund_amount: detail?.refund_amount?.toString?.() ?? "9160",
    });
  };

  const handleCreateProject = async () => {
    try {
      const result = await createMutation.mutateAsync(createForm);
      setSelectedProjectId(result.id);
      setCreateOpen(false);
      toast({ title: "已创建草稿", description: `${result.project_no} 已进入列表` });
    } catch (error) {
      toast({
        title: "创建失败",
        description: error instanceof Error ? error.message : "请重试",
        variant: "destructive",
      });
    }
  };

  const handleAddAttachment = async () => {
    if (!detail) return;
    try {
      await attachmentMutation.mutateAsync({
        projectId: detail.id,
        payload: {
          attachment_type: attachmentForm.attachment_type,
          file_name: attachmentForm.file_name,
          file_url: attachmentForm.file_url,
        },
      });
      setAttachmentOpen(false);
      setAttachmentForm({ attachment_type: "CONTRACTOR_LICENSE", file_name: "", file_url: "/uploads/mock-file.pdf" });
      toast({ title: "附件已添加" });
    } catch (error) {
      toast({
        title: "附件添加失败",
        description: error instanceof Error ? error.message : "请重试",
        variant: "destructive",
      });
    }
  };

  const handleSubmitAction = async () => {
    if (!detail || !pendingAction) return;
    try {
      if (pendingAction === "submit") {
        await submitMutation.mutateAsync({ projectId: detail.id, comment: actionForm.comment });
      } else if (pendingAction === "cancel") {
        await cancelMutation.mutateAsync({ projectId: detail.id, reason: actionForm.comment || "业务撤销" });
      } else if (pendingAction === "property_review") {
        await propertyReviewMutation.mutateAsync({
          projectId: detail.id,
          review_result: actionForm.review_result as "APPROVED" | "RETURNED",
          review_comment: actionForm.comment || "图纸审核完成",
          rectification_requirements: actionForm.rectification_requirements || null,
        });
      } else if (pendingAction === "leader_approval") {
        await leaderMutation.mutateAsync({
          projectId: detail.id,
          action: actionForm.action as "APPROVE" | "REJECT",
          comment: actionForm.comment || "领导审批完成",
        });
      } else if (pendingAction === "deposit_confirm") {
        await depositMutation.mutateAsync({
          projectId: detail.id,
          deposit_amount_expected: Number(actionForm.deposit_amount_expected),
          deposit_amount_received: Number(actionForm.deposit_amount_received),
          received_date: actionForm.received_date,
          finance_comment: actionForm.comment || "",
          action: (actionForm.action as "CONFIRM" | "RETURN") || "CONFIRM",
        });
      } else if (pendingAction === "entry_confirm") {
        await entryMutation.mutateAsync({
          projectId: detail.id,
          entry_result: actionForm.entry_result as "APPROVED" | "DEFERRED" | "RETURNED",
          entry_date: actionForm.entry_date,
          requirements: actionForm.comment || "",
          security_note: actionForm.security_note || "",
        });
      } else if (pendingAction === "completion_submit") {
        await completionMutation.mutateAsync({
          projectId: detail.id,
          actual_finish_date: actionForm.actual_finish_date,
          comment: actionForm.comment || "",
        });
      } else if (pendingAction === "acceptance") {
        await acceptanceMutation.mutateAsync({
          projectId: detail.id,
          acceptance_result: actionForm.acceptance_result as "APPROVED" | "RECTIFICATION",
          acceptance_date: actionForm.acceptance_date,
          acceptance_comment: actionForm.comment || "验收完成",
          rectification_items: actionForm.rectification_items
            ? [{ item_name: actionForm.rectification_items, level: "P1" }]
            : null,
        });
      } else if (pendingAction === "settlement") {
        const deductionAmount = Number(actionForm.deduction_amount || 0);
        await settlementMutation.mutateAsync({
          projectId: detail.id,
          measured_area: Number(actionForm.measured_area),
          actual_power_usage: Number(actionForm.actual_power_usage),
          power_fee_amount: Number(actionForm.power_fee_amount),
          deduction_items: deductionAmount > 0 ? [{ item_name: "现场扣费", amount: deductionAmount }] : [],
          deduction_amount: deductionAmount,
          refund_amount: Number(actionForm.refund_amount),
          settlement_comment: actionForm.comment || "",
        });
      } else if (pendingAction === "refund_approval") {
        await refundApprovalMutation.mutateAsync({
          projectId: detail.id,
          action: actionForm.action as "APPROVE" | "REJECT",
          approved_refund_amount: Number(actionForm.approved_refund_amount),
          comment: actionForm.comment || "退款审批完成",
        });
      } else if (pendingAction === "refund_confirm") {
        await refundConfirmMutation.mutateAsync({
          projectId: detail.id,
          final_refund_amount: Number(actionForm.final_refund_amount),
          refund_date: actionForm.refund_date,
          comment: actionForm.comment || "退款已完成",
        });
      }
      setActionOpen(false);
      setPendingAction(null);
      toast({ title: "流程已更新" });
    } catch (error) {
      toast({
        title: "操作失败",
        description: error instanceof Error ? error.message : "请重试",
        variant: "destructive",
      });
    }
  };

  const renderActionFields = () => {
    switch (pendingAction) {
      case "submit":
      case "cancel":
      case "completion_submit":
        return (
          <>
            {pendingAction === "completion_submit" ? (
              <>
                <Label>实际完工日期</Label>
                <Input
                  type="date"
                  value={actionForm.actual_finish_date || todayString()}
                  onChange={(e) => setActionForm((prev) => ({ ...prev, actual_finish_date: e.target.value }))}
                />
              </>
            ) : null}
            <Label>{pendingAction === "cancel" ? "取消原因" : "说明"}</Label>
            <Textarea value={actionForm.comment || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, comment: e.target.value }))} />
          </>
        );
      case "property_review":
        return (
          <>
            <Label>审图结论</Label>
            <Select value={actionForm.review_result} onValueChange={(value) => setActionForm((prev) => ({ ...prev, review_result: value }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="APPROVED">通过</SelectItem>
                <SelectItem value="RETURNED">退回</SelectItem>
              </SelectContent>
            </Select>
            <Label>审图意见</Label>
            <Textarea value={actionForm.comment || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, comment: e.target.value }))} />
            {actionForm.review_result === "RETURNED" ? (
              <>
                <Label>整改要求</Label>
                <Textarea value={actionForm.rectification_requirements || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, rectification_requirements: e.target.value }))} />
              </>
            ) : null}
          </>
        );
      case "leader_approval":
      case "refund_approval":
        return (
          <>
            <Label>审批结果</Label>
            <Select value={actionForm.action} onValueChange={(value) => setActionForm((prev) => ({ ...prev, action: value }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="APPROVE">通过</SelectItem>
                <SelectItem value="REJECT">驳回</SelectItem>
              </SelectContent>
            </Select>
            {pendingAction === "refund_approval" ? (
              <>
                <Label>审批金额</Label>
                <Input value={actionForm.approved_refund_amount || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, approved_refund_amount: e.target.value }))} />
              </>
            ) : null}
            <Label>审批意见</Label>
            <Textarea value={actionForm.comment || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, comment: e.target.value }))} />
          </>
        );
      case "deposit_confirm":
        return (
          <>
            <Label>处理结果</Label>
            <Select value={actionForm.action || "CONFIRM"} onValueChange={(value) => setActionForm((prev) => ({ ...prev, action: value }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="CONFIRM">确认到账</SelectItem>
                <SelectItem value="RETURN">退回补单据</SelectItem>
              </SelectContent>
            </Select>
            <Label>应缴金额</Label>
            <Input value={actionForm.deposit_amount_expected || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, deposit_amount_expected: e.target.value }))} />
            <Label>实缴金额</Label>
            <Input value={actionForm.deposit_amount_received || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, deposit_amount_received: e.target.value }))} />
            <Label>到账日期</Label>
            <Input type="date" value={actionForm.received_date || todayString()} onChange={(e) => setActionForm((prev) => ({ ...prev, received_date: e.target.value }))} />
            <Label>备注</Label>
            <Textarea value={actionForm.comment || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, comment: e.target.value }))} />
          </>
        );
      case "entry_confirm":
        return (
          <>
            <Label>进场结果</Label>
            <Select value={actionForm.entry_result} onValueChange={(value) => setActionForm((prev) => ({ ...prev, entry_result: value }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="APPROVED">允许进场</SelectItem>
                <SelectItem value="DEFERRED">暂缓进场</SelectItem>
                <SelectItem value="RETURNED">退回整改</SelectItem>
              </SelectContent>
            </Select>
            <Label>进场日期</Label>
            <Input type="date" value={actionForm.entry_date || todayString()} onChange={(e) => setActionForm((prev) => ({ ...prev, entry_date: e.target.value }))} />
            <Label>现场要求</Label>
            <Textarea value={actionForm.comment || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, comment: e.target.value }))} />
          </>
        );
      case "acceptance":
        return (
          <>
            <Label>验收结果</Label>
            <Select value={actionForm.acceptance_result} onValueChange={(value) => setActionForm((prev) => ({ ...prev, acceptance_result: value }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="APPROVED">通过</SelectItem>
                <SelectItem value="RECTIFICATION">整改</SelectItem>
              </SelectContent>
            </Select>
            <Label>验收日期</Label>
            <Input type="date" value={actionForm.acceptance_date || todayString()} onChange={(e) => setActionForm((prev) => ({ ...prev, acceptance_date: e.target.value }))} />
            <Label>验收意见</Label>
            <Textarea value={actionForm.comment || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, comment: e.target.value }))} />
            {actionForm.acceptance_result === "RECTIFICATION" ? (
              <>
                <Label>整改项</Label>
                <Input value={actionForm.rectification_items || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, rectification_items: e.target.value }))} />
              </>
            ) : null}
          </>
        );
      case "settlement":
        return (
          <>
            <Label>实测面积</Label>
            <Input value={actionForm.measured_area || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, measured_area: e.target.value }))} />
            <Label>实际用电</Label>
            <Input value={actionForm.actual_power_usage || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, actual_power_usage: e.target.value }))} />
            <Label>电费金额</Label>
            <Input value={actionForm.power_fee_amount || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, power_fee_amount: e.target.value }))} />
            <Label>扣费金额</Label>
            <Input value={actionForm.deduction_amount || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, deduction_amount: e.target.value }))} />
            <Label>应退金额</Label>
            <Input value={actionForm.refund_amount || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, refund_amount: e.target.value }))} />
            <Label>结算备注</Label>
            <Textarea value={actionForm.comment || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, comment: e.target.value }))} />
          </>
        );
      case "refund_confirm":
        return (
          <>
            <Label>最终退款金额</Label>
            <Input value={actionForm.final_refund_amount || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, final_refund_amount: e.target.value }))} />
            <Label>退款日期</Label>
            <Input type="date" value={actionForm.refund_date || todayString()} onChange={(e) => setActionForm((prev) => ({ ...prev, refund_date: e.target.value }))} />
            <Label>备注</Label>
            <Textarea value={actionForm.comment || ""} onChange={(e) => setActionForm((prev) => ({ ...prev, comment: e.target.value }))} />
          </>
        );
      default:
        return null;
    }
  };

  const renderProjectList = (items: DecorationProjectListItem[]) => (
    <div className="rounded-2xl border border-slate-200 bg-white">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>项目</TableHead>
            <TableHead>品牌</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>计划进场</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.length > 0 ? (
            items.map((item) => (
              <TableRow
                key={item.id}
                className={`cursor-pointer ${selectedProjectId === item.id ? "bg-slate-50" : ""}`}
                onClick={() => setSelectedProjectId(item.id)}
              >
                <TableCell>
                  <div className="font-medium text-slate-900">{item.project_no}</div>
                  <div className="text-xs text-slate-500">{item.store_name}</div>
                </TableCell>
                <TableCell>{item.brand_name}</TableCell>
                <TableCell>
                  <Badge variant="outline" className={STATUS_BADGE_CLASS[item.current_status]}>
                    {item.current_status_name}
                  </Badge>
                </TableCell>
                <TableCell>{item.planned_entry_date}</TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={4} className="py-12 text-center text-slate-500">
                暂无装修项目
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );

  const renderTodoList = (items: DecorationTodoItem[]) => (
    <div className="rounded-2xl border border-slate-200 bg-white">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>待办节点</TableHead>
            <TableHead>项目编号</TableHead>
            <TableHead>品牌</TableHead>
            <TableHead>到达时间</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.length > 0 ? (
            items.map((item) => (
              <TableRow key={item.workflow_instance_node_id} className="cursor-pointer" onClick={() => setSelectedProjectId(item.project_id)}>
                <TableCell className="font-medium">{item.node_name}</TableCell>
                <TableCell>{item.project_no}</TableCell>
                <TableCell>{item.brand_name}</TableCell>
                <TableCell>{item.arrived_at ? item.arrived_at.slice(0, 16).replace("T", " ") : "-"}</TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={4} className="py-12 text-center text-slate-500">
                当前没有待办
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#fff7ed_0%,#f8fafc_45%,#eef6ff_100%)] p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm text-white">
              <HardHat className="h-4 w-4" />
              装修流程最小闭环
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-900">装修管理</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                当前页面支持 mock 联调。若后端或数据库不可用，会自动回退到本地演示数据，让你先把进场、验收、退款这条主链路跑通。
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              <Sparkles className="h-3.5 w-3.5" />
              API 异常时自动使用 mock 数据
            </div>
            <Button variant="outline" onClick={() => { listQuery.refetch(); todosQuery.refetch(); detailQuery.refetch(); }}>
              <RefreshCw className="mr-2 h-4 w-4" />
              刷新
            </Button>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              新建装修项目
            </Button>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_1fr]">
        <div className="space-y-4">
          <Card className="rounded-2xl">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Filter className="h-4 w-4" />
                查询与切换
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input placeholder="按项目编号、品牌、施工单位搜索" value={keyword} onChange={(e) => setKeyword(e.target.value)} />
              <Tabs value={tab} onValueChange={(value) => setTab(value as DecorationTab)}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="projects">
                    <ScrollText className="mr-2 h-4 w-4" />
                    项目列表
                  </TabsTrigger>
                  <TabsTrigger value="todos">
                    <ClipboardList className="mr-2 h-4 w-4" />
                    我的待办
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="projects" className="mt-4">
                  {renderProjectList(projects)}
                </TabsContent>
                <TabsContent value="todos" className="mt-4">
                  {renderTodoList(todos)}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="rounded-2xl">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle className="text-xl">{detail?.project_no ?? "请选择左侧项目"}</CardTitle>
                  <p className="mt-2 text-sm text-slate-500">{detail?.brand_name ?? "选中项目后可查看详情、附件和流程节点。"}</p>
                </div>
                {detail ? (
                  <Badge variant="outline" className={STATUS_BADGE_CLASS[detail.current_status]}>
                    {detail.current_status_name}
                  </Badge>
                ) : null}
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              {detail ? (
                <>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {detailCards.map((item) => (
                      <div key={item.label} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                        <div className="text-xs uppercase tracking-[0.12em] text-slate-500">{item.label}</div>
                        <div className="mt-2 text-sm font-medium text-slate-900">{item.value}</div>
                      </div>
                    ))}
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-semibold text-slate-900">可执行动作</div>
                      <Button variant="outline" size="sm" onClick={() => setAttachmentOpen(true)} disabled={detail.current_status !== "DRAFT"}>
                        <FileUp className="mr-2 h-4 w-4" />
                        补附件
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {detail.available_actions.length > 0 ? detail.available_actions.map((action) => (
                        <Button
                          key={action}
                          size="sm"
                          variant={action === "submit" || action === "refund_confirm" ? "default" : "outline"}
                          onClick={() => openActionDialog(action)}
                        >
                          {action === "submit" ? <Send className="mr-2 h-4 w-4" /> : null}
                          {action}
                        </Button>
                      )) : (
                        <div className="text-sm text-slate-500">当前状态没有可执行动作</div>
                      )}
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="text-sm font-semibold text-slate-900">空间与附件</div>
                    <div className="rounded-2xl border border-slate-200">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>空间</TableHead>
                            <TableHead>类型</TableHead>
                            <TableHead>面积</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {detail.spaces.map((space) => (
                            <TableRow key={space.id}>
                              <TableCell>{space.space_name ?? space.space_code ?? `#${space.id}`}</TableCell>
                              <TableCell>{space.space_type}</TableCell>
                              <TableCell>{space.applied_area ?? "-"} ㎡</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>

                    <div className="space-y-2">
                      {detail.attachments.map((attachment) => (
                        <div key={attachment.id} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                          <div>
                            <div className="text-sm font-medium text-slate-900">{attachment.file_name}</div>
                            <div className="text-xs text-slate-500">{attachment.attachment_type}</div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={detail.current_status !== "DRAFT"}
                            onClick={() => deleteAttachmentMutation.mutate({ projectId: detail.id, attachmentId: attachment.id })}
                          >
                            删除
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <Separator />

                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="space-y-3">
                      <div className="text-sm font-semibold text-slate-900">流程节点</div>
                      <div className="space-y-2 rounded-2xl border border-slate-200 p-4">
                        {(workflowQuery.data?.workflow_instances ?? []).flatMap((workflow) =>
                          workflow.nodes.map((node) => (
                            <div key={node.id} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                              <div>
                                <div className="text-sm font-medium text-slate-900">{node.node_name}</div>
                                <div className="text-xs text-slate-500">{workflow.flow_type}</div>
                              </div>
                              <Badge variant="outline">{node.status}</Badge>
                            </div>
                          )),
                        )}
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="text-sm font-semibold text-slate-900">时间轴</div>
                      <div className="space-y-2 rounded-2xl border border-slate-200 p-4">
                        {(timelineQuery.data ?? []).map((item) => (
                          <div key={`${item.time}-${item.type}`} className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">
                            <div className="text-xs text-slate-500">{item.time.slice(0, 16).replace("T", " ")}</div>
                            <div className="mt-1 text-sm font-medium text-slate-900">{item.content}</div>
                            <div className="text-xs text-slate-500">{item.operator_name ?? "-"}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-12 text-center text-slate-500">
                  选择左侧项目后查看详情
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>新建装修项目</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>门店</Label>
              <Select value={String(createForm.store_id)} onValueChange={(value) => setCreateForm((prev) => ({ ...prev, store_id: Number(value), spaces: defaultCreateForm(Number(value)).spaces }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(metaQuery.data?.stores ?? []).map((store) => (
                    <SelectItem key={store.store_id} value={String(store.store_id)}>{store.store_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>部门</Label>
              <Select value={String(createForm.department_id)} onValueChange={(value) => setCreateForm((prev) => ({ ...prev, department_id: Number(value) }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(metaQuery.data?.departments ?? []).filter((item) => item.store_id === createForm.store_id).map((dept) => (
                    <SelectItem key={dept.id} value={String(dept.id)}>{dept.dept_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>品牌</Label>
              <Input value={createForm.brand_name} onChange={(e) => setCreateForm((prev) => ({ ...prev, brand_name: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>商户主体</Label>
              <Input value={createForm.tenant_name ?? ""} onChange={(e) => setCreateForm((prev) => ({ ...prev, tenant_name: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>施工单位</Label>
              <Input value={createForm.contractor_name} onChange={(e) => setCreateForm((prev) => ({ ...prev, contractor_name: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>施工负责人</Label>
              <Input value={createForm.contractor_contact} onChange={(e) => setCreateForm((prev) => ({ ...prev, contractor_contact: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>联系电话</Label>
              <Input value={createForm.contractor_phone} onChange={(e) => setCreateForm((prev) => ({ ...prev, contractor_phone: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>装修类型</Label>
              <Select value={createForm.fitout_type} onValueChange={(value) => setCreateForm((prev) => ({ ...prev, fitout_type: value as DecorationProjectCreateInput["fitout_type"] }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(metaQuery.data?.fitout_type_options ?? []).map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>模拟空间选择</Label>
              <Select
                value={createForm.spaces[0]?.space_code ?? currentSpaceOptions[0]?.space_code ?? ""}
                onValueChange={(value) => {
                  const selected = currentSpaceOptions.find((item) => item.space_code === value);
                  if (!selected) return;
                  setCreateForm((prev) => ({
                    ...prev,
                    applied_area: selected.applied_area,
                    spaces: [{
                      space_type: selected.space_type,
                      hall_id: selected.hall_id,
                      business_unit_id: selected.business_unit_id,
                      floor_id: selected.floor_id,
                      space_code: selected.space_code,
                      space_name: selected.space_name,
                      applied_area: selected.applied_area,
                    }],
                  }));
                }}
              >
                <SelectTrigger><SelectValue placeholder="选择一个示例空间" /></SelectTrigger>
                <SelectContent>
                  {currentSpaceOptions.map((space) => (
                    <SelectItem key={space.space_code} value={space.space_code}>{space.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>计划进场</Label>
              <Input type="date" value={createForm.planned_entry_date} onChange={(e) => setCreateForm((prev) => ({ ...prev, planned_entry_date: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>计划完工</Label>
              <Input type="date" value={createForm.planned_finish_date} onChange={(e) => setCreateForm((prev) => ({ ...prev, planned_finish_date: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>申请面积</Label>
              <Input value={createForm.applied_area} onChange={(e) => setCreateForm((prev) => ({ ...prev, applied_area: Number(e.target.value || 0) }))} />
            </div>
            <div className="space-y-2">
              <Label>申请人电话</Label>
              <Input value={createForm.applicant_phone} onChange={(e) => setCreateForm((prev) => ({ ...prev, applicant_phone: e.target.value }))} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>装修原因</Label>
              <Input value={createForm.fitout_reason} onChange={(e) => setCreateForm((prev) => ({ ...prev, fitout_reason: e.target.value }))} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>说明</Label>
              <Textarea value={createForm.description ?? ""} onChange={(e) => setCreateForm((prev) => ({ ...prev, description: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
            <Button onClick={handleCreateProject} disabled={createMutation.isPending}>
              创建草稿
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={attachmentOpen} onOpenChange={setAttachmentOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>补充附件</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-2">
              <Label>附件类型</Label>
              <Select value={attachmentForm.attachment_type} onValueChange={(value) => setAttachmentForm((prev) => ({ ...prev, attachment_type: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(metaQuery.data?.attachment_type_options ?? []).map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>文件名</Label>
              <Input value={attachmentForm.file_name} onChange={(e) => setAttachmentForm((prev) => ({ ...prev, file_name: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>文件地址</Label>
              <Input value={attachmentForm.file_url} onChange={(e) => setAttachmentForm((prev) => ({ ...prev, file_url: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAttachmentOpen(false)}>取消</Button>
            <Button onClick={handleAddAttachment} disabled={attachmentMutation.isPending}>添加</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={actionOpen} onOpenChange={setActionOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>执行动作：{pendingAction}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            {renderActionFields()}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setActionOpen(false)}>取消</Button>
            <Button onClick={handleSubmitAction} disabled={mutationBusy}>
              <BadgeCheck className="mr-2 h-4 w-4" />
              确认提交
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
