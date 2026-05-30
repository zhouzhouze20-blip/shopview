import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  acceptDecoration,
  approveDecorationLeader,
  approveDecorationRefund,
  cancelDecoration,
  confirmDecorationDeposit,
  confirmDecorationEntry,
  confirmDecorationRefund,
  createDecoration,
  createDecorationAttachment,
  deleteDecorationAttachment,
  fetchDecorationDetail,
  fetchDecorationMeta,
  fetchDecorations,
  fetchDecorationTimeline,
  fetchDecorationTodos,
  fetchDecorationWorkflow,
  settleDecoration,
  submitDecoration,
  submitDecorationCompletion,
  updateDecoration,
  reviewDecorationProperty,
} from "@/lib/decorations";

const decorationKeys = {
  all: ["decorations"] as const,
  list: (params?: Record<string, unknown>) => ["decorations", "list", params ?? {}] as const,
  detail: (projectId: number | null) => ["decorations", "detail", projectId] as const,
  meta: () => ["decorations", "meta"] as const,
  todos: () => ["decorations", "todos"] as const,
  workflow: (projectId: number | null) => ["decorations", "workflow", projectId] as const,
  timeline: (projectId: number | null) => ["decorations", "timeline", projectId] as const,
};

const invalidateDecorationQueries = async (queryClient: ReturnType<typeof useQueryClient>, projectId?: number | null) => {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: decorationKeys.all }),
    queryClient.invalidateQueries({ queryKey: decorationKeys.meta() }),
    queryClient.invalidateQueries({ queryKey: decorationKeys.todos() }),
    projectId ? queryClient.invalidateQueries({ queryKey: decorationKeys.detail(projectId) }) : Promise.resolve(),
    projectId ? queryClient.invalidateQueries({ queryKey: decorationKeys.workflow(projectId) }) : Promise.resolve(),
    projectId ? queryClient.invalidateQueries({ queryKey: decorationKeys.timeline(projectId) }) : Promise.resolve(),
  ]);
};

export const useDecorationMeta = () =>
  useQuery({
    queryKey: decorationKeys.meta(),
    queryFn: fetchDecorationMeta,
  });

export const useDecorationList = (params?: {
  store_id?: number;
  status?: string;
  keyword?: string;
  mine?: boolean;
  assignee_me?: boolean;
}) =>
  useQuery({
    queryKey: decorationKeys.list(params),
    queryFn: () => fetchDecorations(params),
  });

export const useDecorationDetail = (projectId: number | null) =>
  useQuery({
    queryKey: decorationKeys.detail(projectId),
    queryFn: () => fetchDecorationDetail(projectId as number),
    enabled: projectId != null,
  });

export const useDecorationTodos = () =>
  useQuery({
    queryKey: decorationKeys.todos(),
    queryFn: fetchDecorationTodos,
  });

export const useDecorationWorkflow = (projectId: number | null) =>
  useQuery({
    queryKey: decorationKeys.workflow(projectId),
    queryFn: () => fetchDecorationWorkflow(projectId as number),
    enabled: projectId != null,
  });

export const useDecorationTimeline = (projectId: number | null) =>
  useQuery({
    queryKey: decorationKeys.timeline(projectId),
    queryFn: () => fetchDecorationTimeline(projectId as number),
    enabled: projectId != null,
  });

export const useCreateDecoration = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createDecoration,
    onSuccess: async (data) => {
      await invalidateDecorationQueries(queryClient, data.id);
    },
  });
};

export const useUpdateDecoration = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, payload }: { projectId: number; payload: Parameters<typeof updateDecoration>[1] }) =>
      updateDecoration(projectId, payload),
    onSuccess: async (data) => {
      await invalidateDecorationQueries(queryClient, data.id);
    },
  });
};

export const useCreateDecorationAttachment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, payload }: { projectId: number; payload: Parameters<typeof createDecorationAttachment>[1] }) =>
      createDecorationAttachment(projectId, payload),
    onSuccess: async (data) => {
      await invalidateDecorationQueries(queryClient, data.project_id);
    },
  });
};

export const useDeleteDecorationAttachment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, attachmentId }: { projectId: number; attachmentId: number }) =>
      deleteDecorationAttachment(projectId, attachmentId),
    onSuccess: async (_data, variables) => {
      await invalidateDecorationQueries(queryClient, variables.projectId);
    },
  });
};

const actionMutation = <TVariables extends { projectId: number }>(
  mutationFn: (variables: TVariables) => Promise<unknown>,
) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: async (_data, variables) => {
      await invalidateDecorationQueries(queryClient, variables.projectId);
    },
  });
};

export const useSubmitDecoration = () =>
  actionMutation(({ projectId, comment }: { projectId: number; comment?: string }) => submitDecoration(projectId, comment));

export const useCancelDecoration = () =>
  actionMutation(({ projectId, reason }: { projectId: number; reason: string }) => cancelDecoration(projectId, reason));

export const usePropertyReviewDecoration = () =>
  actionMutation(({ projectId, ...payload }: { projectId: number; review_result: "APPROVED" | "RETURNED"; review_comment: string; rectification_requirements?: string | null }) =>
    reviewDecorationProperty(projectId, payload),
  );

export const useLeaderApproveDecoration = () =>
  actionMutation(({ projectId, ...payload }: { projectId: number; action: "APPROVE" | "REJECT"; comment: string }) =>
    approveDecorationLeader(projectId, payload),
  );

export const useDepositConfirmDecoration = () =>
  actionMutation(({ projectId, ...payload }: { projectId: number; deposit_amount_expected: number; deposit_amount_received: number; received_date: string; finance_comment?: string | null; action?: "CONFIRM" | "RETURN" }) =>
    confirmDecorationDeposit(projectId, payload),
  );

export const useEntryConfirmDecoration = () =>
  actionMutation(({ projectId, ...payload }: { projectId: number; entry_result: "APPROVED" | "DEFERRED" | "RETURNED"; entry_date?: string | null; requirements?: string | null; security_note?: string | null }) =>
    confirmDecorationEntry(projectId, payload),
  );

export const useCompletionSubmitDecoration = () =>
  actionMutation(({ projectId, ...payload }: { projectId: number; actual_finish_date: string; comment?: string | null }) =>
    submitDecorationCompletion(projectId, payload),
  );

export const useAcceptanceDecoration = () =>
  actionMutation(({ projectId, ...payload }: { projectId: number; acceptance_result: "APPROVED" | "RECTIFICATION"; acceptance_date: string; acceptance_comment: string; rectification_items?: Array<Record<string, unknown>> | null }) =>
    acceptDecoration(projectId, payload),
  );

export const useSettlementDecoration = () =>
  actionMutation(({ projectId, ...payload }: { projectId: number; measured_area: number; actual_power_usage: number; power_fee_amount: number; deduction_items?: Array<{ item_name: string; amount: number }>; deduction_amount?: number | null; refund_amount: number; settlement_comment?: string | null }) =>
    settleDecoration(projectId, payload),
  );

export const useRefundApprovalDecoration = () =>
  actionMutation(({ projectId, ...payload }: { projectId: number; action: "APPROVE" | "REJECT"; approved_refund_amount?: number | null; comment: string }) =>
    approveDecorationRefund(projectId, payload),
  );

export const useRefundConfirmDecoration = () =>
  actionMutation(({ projectId, ...payload }: { projectId: number; final_refund_amount: number; refund_date: string; refund_proof_attachment_id?: number | null; comment?: string | null }) =>
    confirmDecorationRefund(projectId, payload),
  );

