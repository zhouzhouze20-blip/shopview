import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";

export type DecorationProjectStatus =
  | "DRAFT"
  | "PENDING_PROPERTY_REVIEW"
  | "PENDING_LEADER_APPROVAL"
  | "PENDING_DEPOSIT_CONFIRM"
  | "PENDING_ENTRY_CONFIRM"
  | "IN_CONSTRUCTION"
  | "PENDING_ACCEPTANCE"
  | "PENDING_SETTLEMENT"
  | "PENDING_REFUND_APPROVAL"
  | "COMPLETED"
  | "REJECTED"
  | "CANCELLED";

export type DecorationAction =
  | "edit"
  | "submit"
  | "cancel"
  | "upload_attachment"
  | "property_review"
  | "leader_approval"
  | "deposit_confirm"
  | "entry_confirm"
  | "completion_submit"
  | "acceptance"
  | "settlement"
  | "refund_approval"
  | "refund_confirm";

export interface DecorationMetaOption {
  label: string;
  value: string;
}

export interface DecorationMetaStore {
  store_id: number;
  store_name: string;
}

export interface DecorationMetaDepartment {
  id: number;
  dept_name: string;
  store_id: number;
}

export interface DecorationMetaSchema {
  status_options: DecorationMetaOption[];
  attachment_type_options: DecorationMetaOption[];
  fitout_type_options: DecorationMetaOption[];
  stores: DecorationMetaStore[];
  departments: DecorationMetaDepartment[];
  workflow_node_options: DecorationMetaOption[];
}

export interface DecorationProjectSpace {
  id: number;
  project_id: number;
  space_type: "UNIT";
  business_unit_id?: number | null;
  floor_id?: number | null;
  space_code?: string | null;
  space_name?: string | null;
  applied_area?: number | null;
  measured_area?: number | null;
  remarks?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface DecorationAttachment {
  id: number;
  project_id: number;
  attachment_type: string;
  file_name: string;
  file_url: string;
  file_size?: number | null;
  mime_type?: string | null;
  related_node_code?: string | null;
  extra_data?: Record<string, unknown> | null;
  uploaded_by: number;
  uploaded_at: string;
}

export interface DecorationWorkflowSummary {
  flow_type?: "ENTRY" | "REFUND" | null;
  current_node_code?: string | null;
  current_assignee_user_id?: number | null;
}

export interface DecorationNodeResultSummary {
  property_review?: Record<string, unknown> | null;
  deposit_confirm?: Record<string, unknown> | null;
  entry_confirm?: Record<string, unknown> | null;
  acceptance?: Record<string, unknown> | null;
  settlement?: Record<string, unknown> | null;
  refund?: Record<string, unknown> | null;
}

export interface DecorationProjectListItem {
  id: number;
  project_no: string;
  store_id: number;
  store_name?: string | null;
  contract_no?: string | null;
  brand_name: string;
  contractor_name: string;
  applicant_user_id: number;
  applicant_name?: string | null;
  current_status: DecorationProjectStatus;
  current_status_name?: string | null;
  current_node_code?: string | null;
  current_assignee_user_id?: number | null;
  current_assignee_name?: string | null;
  planned_entry_date: string;
  planned_finish_date: string;
  updated_at?: string | null;
}

export interface DecorationProjectDetail extends DecorationProjectListItem {
  department_id: number;
  department_name?: string | null;
  applicant_phone: string;
  contract_status?: string | null;
  contract_start_date?: string | null;
  contract_end_date?: string | null;
  tenant_name?: string | null;
  contractor_contact: string;
  contractor_phone: string;
  fitout_type: string;
  fitout_reason: string;
  description?: string | null;
  actual_entry_date?: string | null;
  actual_finish_date?: string | null;
  applied_area: number;
  deposit_amount?: number | null;
  actual_measured_area?: number | null;
  actual_power_usage?: number | null;
  power_fee_amount?: number | null;
  deduction_amount?: number | null;
  refund_amount?: number | null;
  is_closed: boolean;
  closed_at?: string | null;
  reject_reason?: string | null;
  cancel_reason?: string | null;
  oa_ref_no?: string | null;
  spaces: DecorationProjectSpace[];
  attachments: DecorationAttachment[];
  workflow_summary?: DecorationWorkflowSummary | null;
  node_results?: DecorationNodeResultSummary | null;
  available_actions: DecorationAction[];
  created_at: string;
}

export interface DecorationTodoItem {
  workflow_instance_node_id: number;
  project_id: number;
  project_no: string;
  node_code: string;
  node_name: string;
  store_name?: string | null;
  brand_name: string;
  applicant_name?: string | null;
  current_status: DecorationProjectStatus;
  arrived_at?: string | null;
  is_overdue: boolean;
}

export interface DecorationTimelineItem {
  time: string;
  type: string;
  operator_name?: string | null;
  content: string;
}

export interface WorkflowInstanceNode {
  id: number;
  node_code: string;
  node_name: string;
  node_order: number;
  assignee_user_id?: number | null;
  status: string;
  arrived_at?: string | null;
  acted_at?: string | null;
  action_result?: string | null;
  comment?: string | null;
}

export interface WorkflowInstance {
  id: number;
  flow_type: "ENTRY" | "REFUND";
  status: string;
  current_node_code?: string | null;
  nodes: WorkflowInstanceNode[];
}

export interface DecorationWorkflowDetail {
  workflow_instances: WorkflowInstance[];
}

export interface DecorationProjectCreateInput {
  store_id: number;
  department_id: number;
  applicant_phone: string;
  contract_no: string;
  brand_name: string;
  tenant_name?: string;
  contractor_name: string;
  contractor_contact: string;
  contractor_phone: string;
  fitout_type: "NEW" | "REMODEL" | "REFRESH";
  fitout_reason: string;
  description?: string;
  planned_entry_date: string;
  planned_finish_date: string;
  applied_area: number;
  spaces: Array<{
    space_type: "UNIT";
    business_unit_id?: number;
    floor_id?: number;
    space_code?: string;
    space_name?: string;
    applied_area?: number;
  }>;
}

export type DecorationProjectUpdateInput = Partial<DecorationProjectCreateInput>;

export interface DecorationActionResponse {
  message: string;
  project_id: number;
  current_status: DecorationProjectStatus;
  current_node_code?: string | null;
}

export interface DecorationAttachmentCreateInput {
  attachment_type: string;
  file_name: string;
  file_url: string;
  file_size?: number;
  mime_type?: string;
  related_node_code?: string;
  extra_data?: Record<string, unknown>;
}

export interface MockSpaceOption {
  label: string;
  store_id: number;
  space_type: "UNIT";
  business_unit_id?: number;
  floor_id: number;
  space_code: string;
  space_name: string;
  applied_area: number;
}

type MockProjectRecord = DecorationProjectDetail & {
  timeline: DecorationTimelineItem[];
  workflow_detail: DecorationWorkflowDetail;
};

const STATUS_LABELS: Record<DecorationProjectStatus, string> = {
  DRAFT: "草稿",
  PENDING_PROPERTY_REVIEW: "待物业审图",
  PENDING_LEADER_APPROVAL: "待领导审批",
  PENDING_DEPOSIT_CONFIRM: "待保证金确认",
  PENDING_ENTRY_CONFIRM: "待进场确认",
  IN_CONSTRUCTION: "施工中",
  PENDING_ACCEPTANCE: "待完工验收",
  PENDING_SETTLEMENT: "待结算确认",
  PENDING_REFUND_APPROVAL: "待退保证金审批",
  COMPLETED: "已完成",
  REJECTED: "已驳回",
  CANCELLED: "已取消",
};

const MOCK_META: DecorationMetaSchema = {
  status_options: Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label })),
  attachment_type_options: [
    { value: "DRAWING_DRAFT", label: "图纸初稿" },
    { value: "CONSTRUCTION_PLAN", label: "施工方案" },
    { value: "CONTRACTOR_LICENSE", label: "施工单位资质" },
    { value: "SAFETY_COMMITMENT", label: "安全承诺书" },
    { value: "DEPOSIT_RECEIPT", label: "保证金单据" },
    { value: "RECTIFICATION_PHOTO", label: "整改照片" },
    { value: "ACCEPTANCE_FILE", label: "验收附件" },
    { value: "SETTLEMENT_FILE", label: "结算附件" },
    { value: "REFUND_PROOF", label: "退款凭证" },
    { value: "OTHER", label: "其他" },
  ],
  fitout_type_options: [
    { value: "NEW", label: "新进场" },
    { value: "REMODEL", label: "改造" },
    { value: "REFRESH", label: "翻新" },
  ],
  stores: [
    { store_id: 601, store_name: "总部店" },
    { store_id: 602, store_name: "东城店" },
  ],
  departments: [
    { id: 801, dept_name: "女装部", store_id: 601 },
    { id: 802, dept_name: "男装部", store_id: 601 },
    { id: 901, dept_name: "珠宝部", store_id: 602 },
  ],
  workflow_node_options: [
    { value: "PROPERTY_REVIEW", label: "物业审图" },
    { value: "LEADER_APPROVAL", label: "领导审批" },
    { value: "DEPOSIT_CONFIRM", label: "保证金确认" },
    { value: "ENTRY_CONFIRM", label: "进场确认" },
    { value: "REFUND_APPROVAL", label: "退款审批" },
    { value: "REFUND_CONFIRM", label: "退款确认" },
  ],
};

const MOCK_SPACES: MockSpaceOption[] = [
  { label: "总部店 2F 东侧单元B12", store_id: 601, space_type: "UNIT", business_unit_id: 2001, floor_id: 102, space_code: "B12", space_name: "东侧单元B12", applied_area: 48 },
  { label: "东城店 1F 珠宝柜位C12", store_id: 602, space_type: "UNIT", business_unit_id: 2101, floor_id: 201, space_code: "C12", space_name: "珠宝柜位C12", applied_area: 62 },
];

const MOCK_ACTORS = {
  applicant: { id: 12, name: "张三" },
  property: { id: 21, name: "李四" },
  leader: { id: 31, name: "王总" },
  finance: { id: 41, name: "陈会计" },
};

let mockProjectSeq = 3;
let mockAttachmentSeq = 10;
let mockWorkflowSeq = 100;
let mockWorkflowNodeSeq = 1000;

const isoNow = () => new Date().toISOString();
const dateOnly = (value?: string) => (value ? value : new Date().toISOString().slice(0, 10));
const money = (value: number | undefined | null) => (value == null ? null : Number(value));

const makeAvailableActions = (status: DecorationProjectStatus): DecorationAction[] => {
  switch (status) {
    case "DRAFT":
      return ["edit", "upload_attachment", "submit", "cancel"];
    case "PENDING_PROPERTY_REVIEW":
      return ["property_review"];
    case "PENDING_LEADER_APPROVAL":
      return ["leader_approval"];
    case "PENDING_DEPOSIT_CONFIRM":
      return ["deposit_confirm"];
    case "PENDING_ENTRY_CONFIRM":
      return ["entry_confirm"];
    case "IN_CONSTRUCTION":
      return ["completion_submit", "cancel"];
    case "PENDING_ACCEPTANCE":
      return ["acceptance"];
    case "PENDING_SETTLEMENT":
      return ["settlement"];
    case "PENDING_REFUND_APPROVAL":
      return ["refund_approval", "refund_confirm"];
    default:
      return [];
  }
};

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

const initialMockProjects = (): MockProjectRecord[] => {
  const created = isoNow();
  return [
    {
      id: 1,
      project_no: "DEC20260426001",
      store_id: 601,
      store_name: "总部店",
      contract_no: "HT202605001",
      brand_name: "MORI Atelier",
      contractor_name: "星河装饰",
      applicant_user_id: MOCK_ACTORS.applicant.id,
      applicant_name: MOCK_ACTORS.applicant.name,
      current_status: "DRAFT",
      current_status_name: STATUS_LABELS.DRAFT,
      current_node_code: null,
      current_assignee_user_id: null,
      current_assignee_name: null,
      planned_entry_date: "2026-05-08",
      planned_finish_date: "2026-05-22",
      updated_at: created,
      department_id: 801,
      department_name: "女装部",
      applicant_phone: "13800000000",
      contract_status: "B",
      contract_start_date: "2026-05-01",
      contract_end_date: "2027-04-30",
      tenant_name: "上海沐里商贸有限公司",
      contractor_contact: "王工",
      contractor_phone: "13900000000",
      fitout_type: "REMODEL",
      fitout_reason: "柜位形象升级",
      description: "门头、灯带与试衣间局部翻新。",
      actual_entry_date: null,
      actual_finish_date: null,
      applied_area: 86,
      deposit_amount: 12000,
      actual_measured_area: null,
      actual_power_usage: null,
      power_fee_amount: null,
      deduction_amount: null,
      refund_amount: null,
      is_closed: false,
      closed_at: null,
      reject_reason: null,
      cancel_reason: null,
      oa_ref_no: null,
      spaces: [
        {
          id: 1,
          project_id: 1,
          space_type: "UNIT",
          business_unit_id: 2001,
          floor_id: 101,
          space_code: "B12",
          space_name: "东侧单元B12",
          applied_area: 86,
          measured_area: null,
          remarks: null,
          created_at: created,
          updated_at: created,
        },
      ],
      attachments: [
        {
          id: 1,
          project_id: 1,
          attachment_type: "DRAWING_DRAFT",
          file_name: "中庭A区_初稿.pdf",
          file_url: "/uploads/mock-drawing-a.pdf",
          file_size: 204800,
          mime_type: "application/pdf",
          related_node_code: null,
          extra_data: null,
          uploaded_by: MOCK_ACTORS.applicant.id,
          uploaded_at: created,
        },
        {
          id: 2,
          project_id: 1,
          attachment_type: "CONSTRUCTION_PLAN",
          file_name: "施工方案_v1.docx",
          file_url: "/uploads/mock-plan-a.docx",
          file_size: 102400,
          mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          related_node_code: null,
          extra_data: null,
          uploaded_by: MOCK_ACTORS.applicant.id,
          uploaded_at: created,
        },
      ],
      workflow_summary: null,
      node_results: {},
      available_actions: makeAvailableActions("DRAFT"),
      created_at: created,
      timeline: [
        {
          time: created,
          type: "PROJECT_CREATED",
          operator_name: MOCK_ACTORS.applicant.name,
          content: "创建装修项目",
        },
      ],
      workflow_detail: {
        workflow_instances: [],
      },
    },
    {
      id: 2,
      project_no: "DEC20260426002",
      store_id: 602,
      store_name: "东城店",
      contract_no: "HT202605002",
      brand_name: "CROWN JEWEL",
      contractor_name: "恒艺工程",
      applicant_user_id: MOCK_ACTORS.applicant.id,
      applicant_name: MOCK_ACTORS.applicant.name,
      current_status: "PENDING_PROPERTY_REVIEW",
      current_status_name: STATUS_LABELS.PENDING_PROPERTY_REVIEW,
      current_node_code: "PROPERTY_REVIEW",
      current_assignee_user_id: MOCK_ACTORS.property.id,
      current_assignee_name: MOCK_ACTORS.property.name,
      planned_entry_date: "2026-05-10",
      planned_finish_date: "2026-05-18",
      updated_at: created,
      department_id: 901,
      department_name: "珠宝部",
      applicant_phone: "13800000000",
      contract_status: "B",
      contract_start_date: "2026-05-01",
      contract_end_date: "2027-04-30",
      tenant_name: "冠冕珠宝贸易有限公司",
      contractor_contact: "周工",
      contractor_phone: "13700000000",
      fitout_type: "REFRESH",
      fitout_reason: "珠宝灯柜升级",
      description: "重点调整照明与柜体饰面。",
      actual_entry_date: null,
      actual_finish_date: null,
      applied_area: 62,
      deposit_amount: 9000,
      actual_measured_area: null,
      actual_power_usage: null,
      power_fee_amount: null,
      deduction_amount: null,
      refund_amount: null,
      is_closed: false,
      closed_at: null,
      reject_reason: null,
      cancel_reason: null,
      oa_ref_no: null,
      spaces: [
        {
          id: 2,
          project_id: 2,
          space_type: "UNIT",
          business_unit_id: 2101,
          floor_id: 201,
          space_code: "C12",
          space_name: "珠宝柜位C12",
          applied_area: 62,
          measured_area: null,
          remarks: null,
          created_at: created,
          updated_at: created,
        },
      ],
      attachments: [
        {
          id: 3,
          project_id: 2,
          attachment_type: "DRAWING_DRAFT",
          file_name: "珠宝馆C区_初稿.pdf",
          file_url: "/uploads/mock-drawing-c.pdf",
          file_size: 204800,
          mime_type: "application/pdf",
          related_node_code: null,
          extra_data: null,
          uploaded_by: MOCK_ACTORS.applicant.id,
          uploaded_at: created,
        },
        {
          id: 4,
          project_id: 2,
          attachment_type: "CONSTRUCTION_PLAN",
          file_name: "珠宝馆C区_施工方案.pdf",
          file_url: "/uploads/mock-plan-c.pdf",
          file_size: 204800,
          mime_type: "application/pdf",
          related_node_code: null,
          extra_data: null,
          uploaded_by: MOCK_ACTORS.applicant.id,
          uploaded_at: created,
        },
        {
          id: 5,
          project_id: 2,
          attachment_type: "CONTRACTOR_LICENSE",
          file_name: "恒艺工程_资质.jpg",
          file_url: "/uploads/mock-license-c.jpg",
          file_size: 102400,
          mime_type: "image/jpeg",
          related_node_code: null,
          extra_data: null,
          uploaded_by: MOCK_ACTORS.applicant.id,
          uploaded_at: created,
        },
      ],
      workflow_summary: {
        flow_type: "ENTRY",
        current_node_code: "PROPERTY_REVIEW",
        current_assignee_user_id: MOCK_ACTORS.property.id,
      },
      node_results: {},
      available_actions: makeAvailableActions("PENDING_PROPERTY_REVIEW"),
      created_at: created,
      timeline: [
        {
          time: created,
          type: "PROJECT_CREATED",
          operator_name: MOCK_ACTORS.applicant.name,
          content: "创建装修项目",
        },
        {
          time: created,
          type: "WORKFLOW_SUBMIT",
          operator_name: MOCK_ACTORS.applicant.name,
          content: "提交进场审批",
        },
      ],
      workflow_detail: {
        workflow_instances: [
          {
            id: 100,
            flow_type: "ENTRY",
            status: "RUNNING",
            current_node_code: "PROPERTY_REVIEW",
            nodes: [
              {
                id: 1001,
                node_code: "SUBMIT",
                node_name: "发起申请",
                node_order: 1,
                assignee_user_id: MOCK_ACTORS.applicant.id,
                status: "APPROVED",
                arrived_at: created,
                acted_at: created,
                action_result: "SUBMIT",
                comment: "资料已提交，请审核",
              },
              {
                id: 1002,
                node_code: "PROPERTY_REVIEW",
                node_name: "物业审图",
                node_order: 2,
                assignee_user_id: MOCK_ACTORS.property.id,
                status: "PENDING",
                arrived_at: created,
              },
            ],
          },
        ],
      },
    },
  ];
};

let mockProjects = initialMockProjects();

const delay = (ms = 120) => new Promise((resolve) => setTimeout(resolve, ms));

const mockDetail = (projectId: number) => {
  const item = mockProjects.find((project) => project.id === projectId);
  if (!item) {
    throw new Error("装修项目不存在");
  }
  return clone(item);
};

const updateRecord = (projectId: number, updater: (project: MockProjectRecord) => void) => {
  const item = mockProjects.find((project) => project.id === projectId);
  if (!item) throw new Error("装修项目不存在");
  updater(item);
  item.current_status_name = STATUS_LABELS[item.current_status];
  item.available_actions = makeAvailableActions(item.current_status);
  item.updated_at = isoNow();
  return item;
};

const latestWorkflow = (project: MockProjectRecord, flowType?: "ENTRY" | "REFUND") =>
  [...project.workflow_detail.workflow_instances]
    .filter((item) => !flowType || item.flow_type === flowType)
    .sort((a, b) => b.id - a.id)[0];

const pushTimeline = (project: MockProjectRecord, type: string, operator_name: string, content: string) => {
  project.timeline.push({ time: isoNow(), type, operator_name, content });
};

const ensureRequiredAttachments = (project: MockProjectRecord) => {
  const actual = new Set(project.attachments.map((item) => item.attachment_type));
  const required = ["DRAWING_DRAFT", "CONSTRUCTION_PLAN", "CONTRACTOR_LICENSE"];
  const missing = required.filter((item) => !actual.has(item));
  if (missing.length) {
    throw new Error(`缺少必传附件: ${missing.join(", ")}`);
  }
};

const setWorkflowNodeStatus = (
  workflow: WorkflowInstance,
  nodeCode: string,
  status: string,
  comment?: string,
  actionResult?: string,
) => {
  const node = workflow.nodes.find((item) => item.node_code === nodeCode);
  if (!node) return;
  node.status = status;
  node.comment = comment ?? node.comment;
  node.action_result = actionResult ?? node.action_result;
  node.acted_at = isoNow();
};

const openWorkflowNode = (workflow: WorkflowInstance, nodeCode: string, assignee_user_id: number) => {
  const node = workflow.nodes.find((item) => item.node_code === nodeCode);
  if (!node) return;
  node.status = "PENDING";
  node.assignee_user_id = assignee_user_id;
  node.arrived_at = isoNow();
  workflow.current_node_code = nodeCode;
};

const buildEntryWorkflow = (): WorkflowInstance => ({
  id: mockWorkflowSeq++,
  flow_type: "ENTRY",
  status: "RUNNING",
  current_node_code: "PROPERTY_REVIEW",
  nodes: [
    {
      id: mockWorkflowNodeSeq++,
      node_code: "SUBMIT",
      node_name: "发起申请",
      node_order: 1,
      assignee_user_id: MOCK_ACTORS.applicant.id,
      status: "APPROVED",
      arrived_at: isoNow(),
      acted_at: isoNow(),
      action_result: "SUBMIT",
      comment: "资料已提交，请审核",
    },
    {
      id: mockWorkflowNodeSeq++,
      node_code: "PROPERTY_REVIEW",
      node_name: "物业审图",
      node_order: 2,
      assignee_user_id: MOCK_ACTORS.property.id,
      status: "PENDING",
      arrived_at: isoNow(),
    },
    {
      id: mockWorkflowNodeSeq++,
      node_code: "LEADER_APPROVAL",
      node_name: "领导审批",
      node_order: 3,
      status: "SKIPPED",
    },
    {
      id: mockWorkflowNodeSeq++,
      node_code: "DEPOSIT_CONFIRM",
      node_name: "保证金确认",
      node_order: 4,
      status: "SKIPPED",
    },
    {
      id: mockWorkflowNodeSeq++,
      node_code: "ENTRY_CONFIRM",
      node_name: "进场确认",
      node_order: 5,
      status: "SKIPPED",
    },
  ],
});

const buildRefundWorkflow = (): WorkflowInstance => ({
  id: mockWorkflowSeq++,
  flow_type: "REFUND",
  status: "RUNNING",
  current_node_code: "REFUND_APPROVAL",
  nodes: [
    {
      id: mockWorkflowNodeSeq++,
      node_code: "REFUND_APPROVAL",
      node_name: "退款审批",
      node_order: 1,
      assignee_user_id: MOCK_ACTORS.leader.id,
      status: "PENDING",
      arrived_at: isoNow(),
    },
    {
      id: mockWorkflowNodeSeq++,
      node_code: "REFUND_CONFIRM",
      node_name: "退款确认",
      node_order: 2,
      status: "SKIPPED",
    },
  ],
});

const toListItem = (project: MockProjectRecord): DecorationProjectListItem => ({
  id: project.id,
  project_no: project.project_no,
  store_id: project.store_id,
  store_name: project.store_name,
  brand_name: project.brand_name,
  contractor_name: project.contractor_name,
  applicant_user_id: project.applicant_user_id,
  applicant_name: project.applicant_name,
  current_status: project.current_status,
  current_status_name: STATUS_LABELS[project.current_status],
  current_node_code: project.current_node_code,
  current_assignee_user_id: project.current_assignee_user_id,
  current_assignee_name: project.current_assignee_name,
  planned_entry_date: project.planned_entry_date,
  planned_finish_date: project.planned_finish_date,
  updated_at: project.updated_at,
});

const mockList = async (params?: {
  store_id?: number;
  status?: string;
  keyword?: string;
  mine?: boolean;
  assignee_me?: boolean;
}): Promise<DecorationProjectListItem[]> => {
  await delay();
  let items = [...mockProjects];
  if (params?.store_id) {
    items = items.filter((item) => item.store_id === params.store_id);
  }
  if (params?.status) {
    items = items.filter((item) => item.current_status === params.status);
  }
  if (params?.keyword) {
    const keyword = params.keyword.toLowerCase();
    items = items.filter(
      (item) =>
        item.project_no.toLowerCase().includes(keyword) ||
        item.brand_name.toLowerCase().includes(keyword) ||
        item.contractor_name.toLowerCase().includes(keyword),
    );
  }
  return items.sort((a, b) => b.id - a.id).map(toListItem);
};

const mockTodos = async (): Promise<DecorationTodoItem[]> => {
  await delay();
  return mockProjects
    .filter((item) => makeAvailableActions(item.current_status).some((action) => action !== "edit" && action !== "upload_attachment" && action !== "cancel" && action !== "completion_submit"))
    .map((item) => ({
      workflow_instance_node_id: latestWorkflow(item)?.nodes.find((node) => node.status === "PENDING")?.id ?? item.id,
      project_id: item.id,
      project_no: item.project_no,
      node_code: item.current_node_code ?? "DRAFT",
      node_name: STATUS_LABELS[item.current_status],
      store_name: item.store_name,
      brand_name: item.brand_name,
      applicant_name: item.applicant_name,
      current_status: item.current_status,
      arrived_at: item.updated_at,
      is_overdue: false,
    }));
};

const mockMeta = async (): Promise<DecorationMetaSchema> => {
  await delay(60);
  return clone(MOCK_META);
};

const mockCreate = async (payload: DecorationProjectCreateInput): Promise<DecorationProjectDetail> => {
  await delay();
  const id = ++mockProjectSeq;
  const store = MOCK_META.stores.find((item) => item.store_id === payload.store_id);
  const department = MOCK_META.departments.find((item) => item.id === payload.department_id);
  const now = isoNow();
  const record: MockProjectRecord = {
    id,
    project_no: `DEC${new Date().toISOString().slice(0, 10).split("-").join("")}${String(id).padStart(3, "0")}`,
    store_id: payload.store_id,
    store_name: store?.store_name ?? `门店${payload.store_id}`,
    contract_no: payload.contract_no,
    brand_name: payload.brand_name,
    contractor_name: payload.contractor_name,
    applicant_user_id: MOCK_ACTORS.applicant.id,
    applicant_name: MOCK_ACTORS.applicant.name,
    current_status: "DRAFT",
    current_status_name: STATUS_LABELS.DRAFT,
    current_node_code: null,
    current_assignee_user_id: null,
    current_assignee_name: null,
    planned_entry_date: payload.planned_entry_date,
    planned_finish_date: payload.planned_finish_date,
    updated_at: now,
    department_id: payload.department_id,
    department_name: department?.dept_name ?? `部门${payload.department_id}`,
    applicant_phone: payload.applicant_phone,
    contract_status: null,
    contract_start_date: null,
    contract_end_date: null,
    tenant_name: payload.tenant_name ?? null,
    contractor_contact: payload.contractor_contact,
    contractor_phone: payload.contractor_phone,
    fitout_type: payload.fitout_type,
    fitout_reason: payload.fitout_reason,
    description: payload.description ?? null,
    actual_entry_date: null,
    actual_finish_date: null,
    applied_area: payload.applied_area,
    deposit_amount: Math.round(payload.applied_area * 120),
    actual_measured_area: null,
    actual_power_usage: null,
    power_fee_amount: null,
    deduction_amount: null,
    refund_amount: null,
    is_closed: false,
    closed_at: null,
    reject_reason: null,
    cancel_reason: null,
    oa_ref_no: null,
    spaces: payload.spaces.map((space, index) => ({
      id: id * 10 + index + 1,
      project_id: id,
      space_type: space.space_type,
      business_unit_id: space.business_unit_id ?? null,
      floor_id: space.floor_id ?? null,
      space_code: space.space_code ?? null,
      space_name: space.space_name ?? null,
      applied_area: space.applied_area ?? payload.applied_area,
      measured_area: null,
      remarks: null,
      created_at: now,
      updated_at: now,
    })),
    attachments: [],
    workflow_summary: null,
    node_results: {},
    available_actions: makeAvailableActions("DRAFT"),
    created_at: now,
    timeline: [{ time: now, type: "PROJECT_CREATED", operator_name: MOCK_ACTORS.applicant.name, content: "创建装修项目" }],
    workflow_detail: { workflow_instances: [] },
  };
  mockProjects = [record, ...mockProjects];
  return clone(record);
};

const mockUpdate = async (projectId: number, payload: DecorationProjectUpdateInput): Promise<DecorationProjectDetail> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    if (project.current_status !== "DRAFT") {
      throw new Error("当前状态不允许编辑");
    }
    Object.assign(project, payload);
    if (payload.spaces) {
      project.spaces = payload.spaces.map((space, index) => ({
        id: project.id * 10 + index + 1,
        project_id: project.id,
        space_type: space.space_type,
        business_unit_id: space.business_unit_id ?? null,
        floor_id: space.floor_id ?? null,
        space_code: space.space_code ?? null,
        space_name: space.space_name ?? null,
        applied_area: space.applied_area ?? payload.applied_area ?? project.applied_area,
        measured_area: null,
        remarks: null,
        created_at: project.created_at,
        updated_at: isoNow(),
      }));
    }
    pushTimeline(project, "PROJECT_UPDATED", MOCK_ACTORS.applicant.name, "更新草稿内容");
  });
  return clone(updated);
};

const mockCreateAttachment = async (projectId: number, payload: DecorationAttachmentCreateInput): Promise<DecorationAttachment> => {
  await delay(80);
  const updated = updateRecord(projectId, (project) => {
    project.attachments.push({
      id: ++mockAttachmentSeq,
      project_id: project.id,
      attachment_type: payload.attachment_type,
      file_name: payload.file_name,
      file_url: payload.file_url,
      file_size: payload.file_size ?? null,
      mime_type: payload.mime_type ?? null,
      related_node_code: payload.related_node_code ?? null,
      extra_data: payload.extra_data ?? null,
      uploaded_by: MOCK_ACTORS.applicant.id,
      uploaded_at: isoNow(),
    });
    pushTimeline(project, "ATTACHMENT_CREATED", MOCK_ACTORS.applicant.name, `新增附件：${payload.file_name}`);
  });
  return clone(updated.attachments[updated.attachments.length - 1]);
};

const mockDeleteAttachment = async (projectId: number, attachmentId: number): Promise<{ message: string; success: boolean }> => {
  await delay(80);
  updateRecord(projectId, (project) => {
    project.attachments = project.attachments.filter((item) => item.id !== attachmentId);
    pushTimeline(project, "ATTACHMENT_DELETED", MOCK_ACTORS.applicant.name, `删除附件 #${attachmentId}`);
  });
  return { message: "附件删除成功", success: true };
};

const mockSubmit = async (projectId: number, comment?: string): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    if (project.current_status !== "DRAFT") throw new Error("当前状态不可提交");
    ensureRequiredAttachments(project);
    const workflow = buildEntryWorkflow();
    project.workflow_detail.workflow_instances.push(workflow);
    project.workflow_summary = {
      flow_type: "ENTRY",
      current_node_code: "PROPERTY_REVIEW",
      current_assignee_user_id: MOCK_ACTORS.property.id,
    };
    project.current_status = "PENDING_PROPERTY_REVIEW";
    project.current_node_code = "PROPERTY_REVIEW";
    project.current_assignee_user_id = MOCK_ACTORS.property.id;
    project.current_assignee_name = MOCK_ACTORS.property.name;
    pushTimeline(project, "WORKFLOW_SUBMIT", MOCK_ACTORS.applicant.name, comment || "提交进场审批");
  });
  return { message: "提交成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockCancel = async (projectId: number, reason: string): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    project.current_status = "CANCELLED";
    project.current_node_code = null;
    project.current_assignee_user_id = null;
    project.current_assignee_name = null;
    project.cancel_reason = reason;
    project.is_closed = true;
    project.closed_at = isoNow();
    pushTimeline(project, "PROJECT_CANCELLED", MOCK_ACTORS.applicant.name, reason);
  });
  return { message: "取消成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockPropertyReview = async (projectId: number, payload: { review_result: "APPROVED" | "RETURNED"; review_comment: string; rectification_requirements?: string | null; }): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    const workflow = latestWorkflow(project, "ENTRY");
    if (!workflow) throw new Error("进场流程不存在");
    project.node_results = {
      ...project.node_results,
      property_review: {
        review_result: payload.review_result,
        review_comment: payload.review_comment,
        reviewed_at: isoNow(),
      },
    };
    setWorkflowNodeStatus(workflow, "PROPERTY_REVIEW", payload.review_result === "APPROVED" ? "APPROVED" : "RETURNED", payload.review_comment, payload.review_result);
    if (payload.review_result === "RETURNED") {
      workflow.status = "CANCELLED";
      workflow.current_node_code = null;
      project.current_status = "DRAFT";
      project.current_node_code = null;
      project.current_assignee_user_id = null;
      project.current_assignee_name = null;
      pushTimeline(project, "PROPERTY_REVIEW_RETURNED", MOCK_ACTORS.property.name, payload.rectification_requirements || payload.review_comment);
    } else {
      openWorkflowNode(workflow, "LEADER_APPROVAL", MOCK_ACTORS.leader.id);
      project.current_status = "PENDING_LEADER_APPROVAL";
      project.current_node_code = "LEADER_APPROVAL";
      project.current_assignee_user_id = MOCK_ACTORS.leader.id;
      project.current_assignee_name = MOCK_ACTORS.leader.name;
      project.workflow_summary = {
        flow_type: "ENTRY",
        current_node_code: "LEADER_APPROVAL",
        current_assignee_user_id: MOCK_ACTORS.leader.id,
      };
      pushTimeline(project, "PROPERTY_REVIEW_APPROVED", MOCK_ACTORS.property.name, payload.review_comment);
    }
  });
  return { message: "审图处理成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockLeaderApproval = async (projectId: number, payload: { action: "APPROVE" | "REJECT"; comment: string; }): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    const workflow = latestWorkflow(project, "ENTRY");
    if (!workflow) throw new Error("进场流程不存在");
    setWorkflowNodeStatus(workflow, "LEADER_APPROVAL", payload.action === "APPROVE" ? "APPROVED" : "REJECTED", payload.comment, payload.action);
    if (payload.action === "REJECT") {
      workflow.status = "REJECTED";
      workflow.current_node_code = null;
      project.current_status = "REJECTED";
      project.current_node_code = null;
      project.current_assignee_user_id = null;
      project.current_assignee_name = null;
      project.is_closed = true;
      project.closed_at = isoNow();
      project.reject_reason = payload.comment;
      pushTimeline(project, "LEADER_REJECTED", MOCK_ACTORS.leader.name, payload.comment);
    } else {
      openWorkflowNode(workflow, "DEPOSIT_CONFIRM", MOCK_ACTORS.finance.id);
      project.current_status = "PENDING_DEPOSIT_CONFIRM";
      project.current_node_code = "DEPOSIT_CONFIRM";
      project.current_assignee_user_id = MOCK_ACTORS.finance.id;
      project.current_assignee_name = MOCK_ACTORS.finance.name;
      project.workflow_summary = {
        flow_type: "ENTRY",
        current_node_code: "DEPOSIT_CONFIRM",
        current_assignee_user_id: MOCK_ACTORS.finance.id,
      };
      pushTimeline(project, "LEADER_APPROVED", MOCK_ACTORS.leader.name, payload.comment);
    }
  });
  return { message: "审批处理成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockDepositConfirm = async (
  projectId: number,
  payload: { deposit_amount_expected: number; deposit_amount_received: number; received_date: string; finance_comment?: string | null; action?: "CONFIRM" | "RETURN"; },
): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    const workflow = latestWorkflow(project, "ENTRY");
    if (!workflow) throw new Error("进场流程不存在");
    project.deposit_amount = payload.deposit_amount_expected;
    project.node_results = {
      ...project.node_results,
      deposit_confirm: {
        deposit_amount_received: payload.deposit_amount_received,
        received_date: payload.received_date,
      },
    };
    setWorkflowNodeStatus(
      workflow,
      "DEPOSIT_CONFIRM",
      payload.action === "RETURN" ? "RETURNED" : "APPROVED",
      payload.finance_comment ?? undefined,
      payload.action === "RETURN" ? "RETURN" : "CONFIRM",
    );
    if (payload.action === "RETURN") {
      workflow.status = "CANCELLED";
      workflow.current_node_code = null;
      project.current_status = "DRAFT";
      project.current_node_code = null;
      project.current_assignee_user_id = null;
      project.current_assignee_name = null;
      pushTimeline(project, "DEPOSIT_RETURNED", MOCK_ACTORS.finance.name, payload.finance_comment || "退回补充单据");
    } else {
      openWorkflowNode(workflow, "ENTRY_CONFIRM", MOCK_ACTORS.property.id);
      project.current_status = "PENDING_ENTRY_CONFIRM";
      project.current_node_code = "ENTRY_CONFIRM";
      project.current_assignee_user_id = MOCK_ACTORS.property.id;
      project.current_assignee_name = MOCK_ACTORS.property.name;
      project.workflow_summary = {
        flow_type: "ENTRY",
        current_node_code: "ENTRY_CONFIRM",
        current_assignee_user_id: MOCK_ACTORS.property.id,
      };
      pushTimeline(project, "DEPOSIT_CONFIRMED", MOCK_ACTORS.finance.name, payload.finance_comment || "保证金已确认到账");
    }
  });
  return { message: "保证金处理成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockEntryConfirm = async (
  projectId: number,
  payload: { entry_result: "APPROVED" | "DEFERRED" | "RETURNED"; entry_date?: string | null; requirements?: string | null; security_note?: string | null; },
): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    const workflow = latestWorkflow(project, "ENTRY");
    if (!workflow) throw new Error("进场流程不存在");
    project.node_results = {
      ...project.node_results,
      entry_confirm: {
        entry_result: payload.entry_result,
        entry_date: payload.entry_date,
      },
    };
    setWorkflowNodeStatus(workflow, "ENTRY_CONFIRM", payload.entry_result === "APPROVED" ? "APPROVED" : payload.entry_result === "RETURNED" ? "RETURNED" : "PENDING", payload.requirements ?? undefined, payload.entry_result);
    if (payload.entry_result === "APPROVED") {
      workflow.status = "COMPLETED";
      workflow.current_node_code = null;
      project.current_status = "IN_CONSTRUCTION";
      project.current_node_code = null;
      project.current_assignee_user_id = null;
      project.current_assignee_name = null;
      project.actual_entry_date = payload.entry_date ?? dateOnly();
      pushTimeline(project, "ENTRY_CONFIRMED", MOCK_ACTORS.property.name, payload.requirements || "允许进场");
    } else if (payload.entry_result === "RETURNED") {
      workflow.status = "CANCELLED";
      workflow.current_node_code = null;
      project.current_status = "DRAFT";
      project.current_node_code = null;
      project.current_assignee_user_id = null;
      project.current_assignee_name = null;
      pushTimeline(project, "ENTRY_RETURNED", MOCK_ACTORS.property.name, payload.requirements || "退回整改");
    } else {
      project.current_status = "PENDING_ENTRY_CONFIRM";
      project.current_node_code = "ENTRY_CONFIRM";
      project.current_assignee_user_id = MOCK_ACTORS.property.id;
      project.current_assignee_name = MOCK_ACTORS.property.name;
      pushTimeline(project, "ENTRY_DEFERRED", MOCK_ACTORS.property.name, payload.requirements || "暂缓进场");
    }
  });
  return { message: "进场处理成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockCompletionSubmit = async (projectId: number, payload: { actual_finish_date: string; comment?: string | null; }): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    project.actual_finish_date = payload.actual_finish_date;
    project.current_status = "PENDING_ACCEPTANCE";
    project.current_node_code = "ACCEPTANCE";
    project.current_assignee_user_id = MOCK_ACTORS.property.id;
    project.current_assignee_name = MOCK_ACTORS.property.name;
    pushTimeline(project, "COMPLETION_SUBMITTED", MOCK_ACTORS.applicant.name, payload.comment || "提交完工验收");
  });
  return { message: "已提交完工验收", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockAcceptance = async (
  projectId: number,
  payload: { acceptance_result: "APPROVED" | "RECTIFICATION"; acceptance_date: string; acceptance_comment: string; rectification_items?: Array<Record<string, unknown>> | null; },
): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    project.node_results = {
      ...project.node_results,
      acceptance: {
        acceptance_result: payload.acceptance_result,
        acceptance_date: payload.acceptance_date,
      },
    };
    if (payload.acceptance_result === "RECTIFICATION") {
      project.current_status = "IN_CONSTRUCTION";
      project.current_node_code = null;
      project.current_assignee_user_id = null;
      project.current_assignee_name = null;
      pushTimeline(project, "ACCEPTANCE_RECTIFICATION", MOCK_ACTORS.property.name, payload.acceptance_comment);
    } else {
      project.current_status = "PENDING_SETTLEMENT";
      project.current_node_code = "SETTLEMENT";
      project.current_assignee_user_id = MOCK_ACTORS.property.id;
      project.current_assignee_name = MOCK_ACTORS.property.name;
      pushTimeline(project, "ACCEPTANCE_APPROVED", MOCK_ACTORS.property.name, payload.acceptance_comment);
    }
  });
  return { message: "验收处理成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockSettlement = async (
  projectId: number,
  payload: { measured_area: number; actual_power_usage: number; power_fee_amount: number; deduction_items?: Array<{ item_name: string; amount: number }>; deduction_amount?: number | null; refund_amount: number; settlement_comment?: string | null; },
): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    project.actual_measured_area = payload.measured_area;
    project.actual_power_usage = payload.actual_power_usage;
    project.power_fee_amount = payload.power_fee_amount;
    project.deduction_amount = payload.deduction_amount ?? null;
    project.refund_amount = payload.refund_amount;
    project.node_results = {
      ...project.node_results,
      settlement: {
        refund_amount: payload.refund_amount,
        confirmed_at: isoNow(),
      },
    };
    const refundWorkflow = buildRefundWorkflow();
    project.workflow_detail.workflow_instances.push(refundWorkflow);
    project.workflow_summary = {
      flow_type: "REFUND",
      current_node_code: "REFUND_APPROVAL",
      current_assignee_user_id: MOCK_ACTORS.leader.id,
    };
    project.current_status = "PENDING_REFUND_APPROVAL";
    project.current_node_code = "REFUND_APPROVAL";
    project.current_assignee_user_id = MOCK_ACTORS.leader.id;
    project.current_assignee_name = MOCK_ACTORS.leader.name;
    pushTimeline(project, "SETTLEMENT_CONFIRMED", MOCK_ACTORS.property.name, payload.settlement_comment || "结算确认完成");
  });
  return { message: "结算确认成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockRefundApproval = async (
  projectId: number,
  payload: { action: "APPROVE" | "REJECT"; approved_refund_amount?: number | null; comment: string; },
): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    const workflow = latestWorkflow(project, "REFUND");
    if (!workflow) throw new Error("退款流程不存在");
    setWorkflowNodeStatus(workflow, "REFUND_APPROVAL", payload.action === "APPROVE" ? "APPROVED" : "REJECTED", payload.comment, payload.action);
    if (payload.action === "REJECT") {
      workflow.status = "REJECTED";
      workflow.current_node_code = null;
      project.current_status = "PENDING_SETTLEMENT";
      project.current_node_code = "SETTLEMENT";
      project.current_assignee_user_id = MOCK_ACTORS.property.id;
      project.current_assignee_name = MOCK_ACTORS.property.name;
      pushTimeline(project, "REFUND_REJECTED", MOCK_ACTORS.leader.name, payload.comment);
    } else {
      openWorkflowNode(workflow, "REFUND_CONFIRM", MOCK_ACTORS.finance.id);
      project.current_status = "PENDING_REFUND_APPROVAL";
      project.current_node_code = "REFUND_CONFIRM";
      project.current_assignee_user_id = MOCK_ACTORS.finance.id;
      project.current_assignee_name = MOCK_ACTORS.finance.name;
      project.node_results = {
        ...project.node_results,
        refund: {
          approved_refund_amount: payload.approved_refund_amount,
        },
      };
      project.workflow_summary = {
        flow_type: "REFUND",
        current_node_code: "REFUND_CONFIRM",
        current_assignee_user_id: MOCK_ACTORS.finance.id,
      };
      pushTimeline(project, "REFUND_APPROVED", MOCK_ACTORS.leader.name, payload.comment);
    }
  });
  return { message: "退款审批处理成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const mockRefundConfirm = async (
  projectId: number,
  payload: { final_refund_amount: number; refund_date: string; comment?: string | null; },
): Promise<DecorationActionResponse> => {
  await delay();
  const updated = updateRecord(projectId, (project) => {
    const workflow = latestWorkflow(project, "REFUND");
    if (!workflow) throw new Error("退款流程不存在");
    setWorkflowNodeStatus(workflow, "REFUND_CONFIRM", "APPROVED", payload.comment ?? undefined, "CONFIRM");
    workflow.status = "COMPLETED";
    workflow.current_node_code = null;
    project.current_status = "COMPLETED";
    project.current_node_code = null;
    project.current_assignee_user_id = null;
    project.current_assignee_name = null;
    project.is_closed = true;
    project.closed_at = isoNow();
    project.node_results = {
      ...project.node_results,
      refund: {
        final_refund_amount: payload.final_refund_amount,
        refund_date: payload.refund_date,
      },
    };
    pushTimeline(project, "REFUND_COMPLETED", MOCK_ACTORS.finance.name, payload.comment || "退款完成");
  });
  return { message: "退款确认成功", project_id: updated.id, current_status: updated.current_status, current_node_code: updated.current_node_code };
};

const queryString = (params?: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const value = search.toString();
  return value ? `?${value}` : "";
};

export const isDecorationMockEnabled = import.meta.env.VITE_ENABLE_DECORATION_MOCK === "true";

const withMock = async <T,>(apiCall: () => Promise<T>, mockCall: () => Promise<T>): Promise<T> => {
  try {
    return await apiCall();
  } catch (error) {
    if (!isDecorationMockEnabled) {
      throw error;
    }
    console.warn("[decorations] API unavailable, fallback to mock mode", error);
    return await mockCall();
  }
};

export const getMockSpaceOptions = (storeId?: number | null) =>
  MOCK_SPACES.filter((item) => !storeId || item.store_id === storeId);

export const fetchDecorationMeta = () =>
  withMock(() => apiGet<DecorationMetaSchema>("/api/decorations/meta"), mockMeta);

export const fetchDecorations = (params?: {
  store_id?: number;
  status?: string;
  keyword?: string;
  mine?: boolean;
  assignee_me?: boolean;
}) =>
  withMock(
    () => apiGet<DecorationProjectListItem[]>(`/api/decorations${queryString(params)}`),
    () => mockList(params),
  );

export const fetchDecorationDetail = (projectId: number) =>
  withMock(
    () => apiGet<DecorationProjectDetail>(`/api/decorations/${projectId}`),
    async () => {
      await delay();
      return mockDetail(projectId);
    },
  );

export const fetchDecorationTodos = () =>
  withMock(() => apiGet<DecorationTodoItem[]>("/api/decorations/todos"), mockTodos);

export const fetchDecorationWorkflow = (projectId: number) =>
  withMock(
    () => apiGet<DecorationWorkflowDetail>(`/api/decorations/${projectId}/workflow`),
    async () => {
      await delay();
      return clone(mockDetail(projectId).workflow_detail);
    },
  );

export const fetchDecorationTimeline = (projectId: number) =>
  withMock(
    () => apiGet<DecorationTimelineItem[]>(`/api/decorations/${projectId}/timeline`),
    async () => {
      await delay();
      return clone(mockDetail(projectId).timeline);
    },
  );

export const createDecoration = (payload: DecorationProjectCreateInput) =>
  withMock(
    () => apiPost<DecorationProjectDetail>("/api/decorations", payload),
    () => mockCreate(payload),
  );

export const updateDecoration = (projectId: number, payload: DecorationProjectUpdateInput) =>
  withMock(
    () => apiPut<DecorationProjectDetail>(`/api/decorations/${projectId}`, payload),
    () => mockUpdate(projectId, payload),
  );

export const createDecorationAttachment = (projectId: number, payload: DecorationAttachmentCreateInput) =>
  withMock(
    () => apiPost<DecorationAttachment>(`/api/decorations/${projectId}/attachments`, payload),
    () => mockCreateAttachment(projectId, payload),
  );

export const deleteDecorationAttachment = (projectId: number, attachmentId: number) =>
  withMock(
    () => apiDelete<{ message: string; success: boolean }>(`/api/decorations/${projectId}/attachments/${attachmentId}`),
    () => mockDeleteAttachment(projectId, attachmentId),
  );

export const submitDecoration = (projectId: number, comment?: string) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/submit`, { comment }),
    () => mockSubmit(projectId, comment),
  );

export const cancelDecoration = (projectId: number, reason: string) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/cancel`, { reason }),
    () => mockCancel(projectId, reason),
  );

export const reviewDecorationProperty = (
  projectId: number,
  payload: { review_result: "APPROVED" | "RETURNED"; review_comment: string; rectification_requirements?: string | null; },
) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/property-review`, payload),
    () => mockPropertyReview(projectId, payload),
  );

export const approveDecorationLeader = (
  projectId: number,
  payload: { action: "APPROVE" | "REJECT"; comment: string; },
) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/leader-approval`, payload),
    () => mockLeaderApproval(projectId, payload),
  );

export const confirmDecorationDeposit = (
  projectId: number,
  payload: { deposit_amount_expected: number; deposit_amount_received: number; received_date: string; finance_comment?: string | null; action?: "CONFIRM" | "RETURN"; },
) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/deposit-confirm`, payload),
    () => mockDepositConfirm(projectId, payload),
  );

export const confirmDecorationEntry = (
  projectId: number,
  payload: { entry_result: "APPROVED" | "DEFERRED" | "RETURNED"; entry_date?: string | null; requirements?: string | null; security_note?: string | null; },
) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/entry-confirm`, payload),
    () => mockEntryConfirm(projectId, payload),
  );

export const submitDecorationCompletion = (
  projectId: number,
  payload: { actual_finish_date: string; comment?: string | null; },
) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/completion-submit`, payload),
    () => mockCompletionSubmit(projectId, payload),
  );

export const acceptDecoration = (
  projectId: number,
  payload: { acceptance_result: "APPROVED" | "RECTIFICATION"; acceptance_date: string; acceptance_comment: string; rectification_items?: Array<Record<string, unknown>> | null; },
) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/acceptance`, payload),
    () => mockAcceptance(projectId, payload),
  );

export const settleDecoration = (
  projectId: number,
  payload: { measured_area: number; actual_power_usage: number; power_fee_amount: number; deduction_items?: Array<{ item_name: string; amount: number }>; deduction_amount?: number | null; refund_amount: number; settlement_comment?: string | null; },
) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/settlement`, payload),
    () => mockSettlement(projectId, payload),
  );

export const approveDecorationRefund = (
  projectId: number,
  payload: { action: "APPROVE" | "REJECT"; approved_refund_amount?: number | null; comment: string; },
) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/refund-approval`, payload),
    () => mockRefundApproval(projectId, payload),
  );

export const confirmDecorationRefund = (
  projectId: number,
  payload: { final_refund_amount: number; refund_date: string; refund_proof_attachment_id?: number | null; comment?: string | null; },
) =>
  withMock(
    () => apiPost<DecorationActionResponse>(`/api/decorations/${projectId}/refund-confirm`, payload),
    () => mockRefundConfirm(projectId, payload),
  );
