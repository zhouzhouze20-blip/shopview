"""create decoration workflow tables

Revision ID: 9f2b7c6d4e1a
Revises: f2c1a6b7d9e0
Create Date: 2026-04-24 17:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9f2b7c6d4e1a"
down_revision: Union[str, Sequence[str], None] = "f2c1a6b7d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_templates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("template_code", sa.String(length=50), nullable=False),
        sa.Column("template_name", sa.String(length=100), nullable=False),
        sa.Column("business_type", sa.String(length=50), nullable=False),
        sa.Column("scene_code", sa.String(length=50), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["store_id"], ["stores.store_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_code", name="uq_workflow_templates_template_code"),
    )

    op.create_table(
        "decoration_projects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_no", sa.String(length=50), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.BigInteger(), nullable=False),
        sa.Column("applicant_user_id", sa.Integer(), nullable=False),
        sa.Column("applicant_phone", sa.String(length=30), nullable=False),
        sa.Column("brand_name", sa.String(length=200), nullable=False),
        sa.Column("tenant_name", sa.String(length=200), nullable=True),
        sa.Column("contractor_name", sa.String(length=200), nullable=False),
        sa.Column("contractor_contact", sa.String(length=100), nullable=False),
        sa.Column("contractor_phone", sa.String(length=30), nullable=False),
        sa.Column("fitout_type", sa.String(length=30), nullable=False),
        sa.Column("fitout_reason", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("planned_entry_date", sa.Date(), nullable=False),
        sa.Column("planned_finish_date", sa.Date(), nullable=False),
        sa.Column("actual_entry_date", sa.Date(), nullable=True),
        sa.Column("actual_finish_date", sa.Date(), nullable=True),
        sa.Column("applied_area", sa.Numeric(12, 2), nullable=False),
        sa.Column("deposit_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("actual_measured_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("actual_power_usage", sa.Numeric(12, 2), nullable=True),
        sa.Column("power_fee_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("deduction_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("current_status", sa.String(length=40), nullable=False, server_default="DRAFT"),
        sa.Column("current_node_code", sa.String(length=50), nullable=True),
        sa.Column("current_assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("current_workflow_instance_id", sa.BigInteger(), nullable=True),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("oa_ref_no", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "current_status IN ('DRAFT','PENDING_PROPERTY_REVIEW','PENDING_LEADER_APPROVAL',"
            "'PENDING_DEPOSIT_CONFIRM','PENDING_ENTRY_CONFIRM','IN_CONSTRUCTION',"
            "'PENDING_ACCEPTANCE','PENDING_SETTLEMENT','PENDING_REFUND_APPROVAL',"
            "'COMPLETED','REJECTED','CANCELLED')",
            name="ck_decoration_projects_status",
        ),
        sa.ForeignKeyConstraint(["store_id"], ["stores.store_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["applicant_user_id"], ["users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["current_assignee_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_no", name="uq_decoration_projects_project_no"),
    )
    op.create_index("ix_decoration_projects_store_status", "decoration_projects", ["store_id", "current_status"], unique=False)
    op.create_index("ix_decoration_projects_applicant", "decoration_projects", ["applicant_user_id"], unique=False)
    op.create_index("ix_decoration_projects_current_assignee", "decoration_projects", ["current_assignee_user_id"], unique=False)
    op.create_index("ix_decoration_projects_planned_entry_date", "decoration_projects", ["planned_entry_date"], unique=False)

    op.create_table(
        "decoration_project_spaces",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("space_type", sa.String(length=20), nullable=False),
        sa.Column("hall_id", sa.Integer(), nullable=True),
        sa.Column("business_unit_id", sa.BigInteger(), nullable=True),
        sa.Column("floor_id", sa.BigInteger(), nullable=True),
        sa.Column("space_code", sa.String(length=100), nullable=True),
        sa.Column("space_name", sa.String(length=200), nullable=True),
        sa.Column("applied_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("measured_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("space_type IN ('HALL','UNIT')", name="ck_decoration_project_spaces_space_type"),
        sa.CheckConstraint(
            "(space_type = 'HALL' AND hall_id IS NOT NULL AND business_unit_id IS NULL) OR "
            "(space_type = 'UNIT' AND business_unit_id IS NOT NULL AND hall_id IS NULL)",
            name="ck_decoration_project_spaces_target_ref",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["decoration_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hall_id"], ["halls.hall_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decoration_project_spaces_project_id", "decoration_project_spaces", ["project_id"], unique=False)
    op.create_index("ix_decoration_project_spaces_hall_id", "decoration_project_spaces", ["hall_id"], unique=False)
    op.create_index("ix_decoration_project_spaces_business_unit_id", "decoration_project_spaces", ["business_unit_id"], unique=False)

    op.create_table(
        "decoration_attachments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("attachment_type", sa.String(length=40), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("related_node_code", sa.String(length=50), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["decoration_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decoration_attachments_project_id", "decoration_attachments", ["project_id"], unique=False)
    op.create_index("ix_decoration_attachments_type", "decoration_attachments", ["attachment_type"], unique=False)

    op.create_table(
        "workflow_template_nodes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("node_code", sa.String(length=50), nullable=False),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column("node_order", sa.Integer(), nullable=False),
        sa.Column("node_type", sa.String(length=30), nullable=False),
        sa.Column("role_code", sa.String(length=50), nullable=False),
        sa.Column("allow_reject", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allow_return", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("return_target", sa.String(length=50), nullable=True),
        sa.Column("is_final_node", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["template_id"], ["workflow_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "node_code", name="uq_workflow_template_nodes_code"),
        sa.UniqueConstraint("template_id", "node_order", name="uq_workflow_template_nodes_order"),
    )

    op.create_table(
        "workflow_instances",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("flow_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="RUNNING"),
        sa.Column("current_node_code", sa.String(length=50), nullable=True),
        sa.Column("current_assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("started_by", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('RUNNING','COMPLETED','REJECTED','CANCELLED')", name="ck_workflow_instances_status"),
        sa.ForeignKeyConstraint(["project_id"], ["decoration_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["workflow_templates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["current_assignee_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["started_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_instances_project_id", "workflow_instances", ["project_id"], unique=False)
    op.create_index("ix_workflow_instances_current_assignee", "workflow_instances", ["current_assignee_user_id"], unique=False)
    op.create_index("ix_workflow_instances_status", "workflow_instances", ["status"], unique=False)

    op.create_foreign_key(
        "fk_decoration_projects_current_workflow_instance_id",
        "decoration_projects",
        "workflow_instances",
        ["current_workflow_instance_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "workflow_instance_nodes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("workflow_instance_id", sa.BigInteger(), nullable=False),
        sa.Column("template_node_id", sa.BigInteger(), nullable=False),
        sa.Column("node_code", sa.String(length=50), nullable=False),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column("node_order", sa.Integer(), nullable=False),
        sa.Column("assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("arrived_at", sa.DateTime(), nullable=True),
        sa.Column("acted_at", sa.DateTime(), nullable=True),
        sa.Column("action_result", sa.String(length=30), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','RETURNED','SKIPPED')", name="ck_workflow_instance_nodes_status"),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["workflow_instances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_node_id"], ["workflow_template_nodes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_instance_nodes_instance_id", "workflow_instance_nodes", ["workflow_instance_id"], unique=False)
    op.create_index("ix_workflow_instance_nodes_assignee_status", "workflow_instance_nodes", ["assignee_user_id", "status"], unique=False)

    op.create_table(
        "workflow_actions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("workflow_instance_id", sa.BigInteger(), nullable=False),
        sa.Column("workflow_instance_node_id", sa.BigInteger(), nullable=True),
        sa.Column("action_code", sa.String(length=30), nullable=False),
        sa.Column("action_result", sa.String(length=30), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("action_comment", sa.Text(), nullable=True),
        sa.Column("action_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("action_code IN ('SUBMIT','APPROVE','REJECT','RETURN','CANCEL','CONFIRM')", name="ck_workflow_actions_action_code"),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["workflow_instances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_instance_node_id"], ["workflow_instance_nodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_actions_instance_id", "workflow_actions", ["workflow_instance_id"], unique=False)
    op.create_index("ix_workflow_actions_actor_user_id", "workflow_actions", ["actor_user_id"], unique=False)

    op.create_table(
        "decoration_property_reviews",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("workflow_instance_id", sa.BigInteger(), nullable=True),
        sa.Column("review_result", sa.String(length=30), nullable=False),
        sa.Column("review_comment", sa.Text(), nullable=False),
        sa.Column("rectification_requirements", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["decoration_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["workflow_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decoration_property_reviews_project_id", "decoration_property_reviews", ["project_id"], unique=False)

    op.create_table(
        "decoration_deposit_confirms",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("workflow_instance_id", sa.BigInteger(), nullable=True),
        sa.Column("deposit_amount_expected", sa.Numeric(12, 2), nullable=False),
        sa.Column("deposit_amount_received", sa.Numeric(12, 2), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("receipt_attachment_id", sa.BigInteger(), nullable=True),
        sa.Column("finance_comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="CONFIRMED"),
        sa.Column("confirmed_by", sa.Integer(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["decoration_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["workflow_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["receipt_attachment_id"], ["decoration_attachments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decoration_deposit_confirms_project_id", "decoration_deposit_confirms", ["project_id"], unique=False)

    op.create_table(
        "decoration_entry_confirms",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("workflow_instance_id", sa.BigInteger(), nullable=True),
        sa.Column("entry_result", sa.String(length=30), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("security_note", sa.Text(), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["decoration_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["workflow_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decoration_entry_confirms_project_id", "decoration_entry_confirms", ["project_id"], unique=False)

    op.create_table(
        "decoration_acceptances",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("acceptance_result", sa.String(length=30), nullable=False),
        sa.Column("acceptance_date", sa.Date(), nullable=False),
        sa.Column("acceptance_comment", sa.Text(), nullable=False),
        sa.Column("rectification_items", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("accepted_by", sa.Integer(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["decoration_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["accepted_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decoration_acceptances_project_id", "decoration_acceptances", ["project_id"], unique=False)

    op.create_table(
        "decoration_settlements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("measured_area", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual_power_usage", sa.Numeric(12, 2), nullable=False),
        sa.Column("power_fee_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("deduction_items", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deduction_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("settlement_comment", sa.Text(), nullable=True),
        sa.Column("confirmed_by_property", sa.Integer(), nullable=True),
        sa.Column("confirmed_by_finance", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="CONFIRMED"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["decoration_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["confirmed_by_property"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by_finance"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decoration_settlements_project_id", "decoration_settlements", ["project_id"], unique=False)

    op.create_table(
        "decoration_refunds",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("workflow_instance_id", sa.BigInteger(), nullable=True),
        sa.Column("approved_refund_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("final_refund_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("leader_comment", sa.Text(), nullable=True),
        sa.Column("finance_comment", sa.Text(), nullable=True),
        sa.Column("refund_date", sa.Date(), nullable=True),
        sa.Column("refund_proof_attachment_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["decoration_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["workflow_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["refund_proof_attachment_id"], ["decoration_attachments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decoration_refunds_project_id", "decoration_refunds", ["project_id"], unique=False)

    op.execute(
        """
        INSERT INTO roles (role_code, role_name, role_level, is_system, is_active)
        VALUES
            ('decoration_applicant', '装修申请人', 400, TRUE, TRUE),
            ('decoration_property', '装修物业经办', 650, TRUE, TRUE),
            ('decoration_leader', '装修审批领导', 750, TRUE, TRUE),
            ('decoration_finance', '装修财务', 550, TRUE, TRUE),
            ('decoration_security', '装修保安协同', 300, TRUE, TRUE),
            ('decoration_admin', '装修流程管理员', 850, TRUE, TRUE)
        ON CONFLICT (role_code) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO permissions (permission_code, permission_name, module_code, action_code)
        VALUES
            ('decoration.view', '查看装修项目', 'decoration', 'view'),
            ('decoration.create', '新建装修项目', 'decoration', 'create'),
            ('decoration.edit', '编辑装修项目', 'decoration', 'edit'),
            ('decoration.submit', '提交装修审批', 'decoration', 'submit'),
            ('decoration.todo.view', '查看装修待办', 'decoration', 'todo_view'),
            ('decoration.property_review', '物业审图', 'decoration', 'property_review'),
            ('decoration.leader_approve', '领导审批装修', 'decoration', 'leader_approve'),
            ('decoration.deposit_confirm', '确认装修保证金', 'decoration', 'deposit_confirm'),
            ('decoration.entry_confirm', '确认装修进场', 'decoration', 'entry_confirm'),
            ('decoration.acceptance', '装修验收', 'decoration', 'acceptance'),
            ('decoration.settlement', '装修结算', 'decoration', 'settlement'),
            ('decoration.refund_approve', '审批退保证金', 'decoration', 'refund_approve'),
            ('decoration.refund_confirm', '确认退保证金', 'decoration', 'refund_confirm'),
            ('decoration.cancel', '取消装修项目', 'decoration', 'cancel')
        ON CONFLICT (permission_code) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.permission_code IN (
            'decoration.view',
            'decoration.create',
            'decoration.edit',
            'decoration.submit',
            'decoration.todo.view',
            'decoration.property_review',
            'decoration.leader_approve',
            'decoration.deposit_confirm',
            'decoration.entry_confirm',
            'decoration.acceptance',
            'decoration.settlement',
            'decoration.refund_approve',
            'decoration.refund_confirm',
            'decoration.cancel'
        )
        WHERE r.role_code = 'super_admin'
        ON CONFLICT DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.permission_code IN (
            'decoration.view',
            'decoration.create',
            'decoration.edit',
            'decoration.submit',
            'decoration.todo.view',
            'decoration.cancel'
        )
        WHERE r.role_code = 'decoration_applicant'
        ON CONFLICT DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.permission_code IN (
            'decoration.view',
            'decoration.todo.view',
            'decoration.property_review',
            'decoration.entry_confirm',
            'decoration.acceptance',
            'decoration.settlement'
        )
        WHERE r.role_code = 'decoration_property'
        ON CONFLICT DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.permission_code IN (
            'decoration.view',
            'decoration.todo.view',
            'decoration.leader_approve',
            'decoration.refund_approve'
        )
        WHERE r.role_code = 'decoration_leader'
        ON CONFLICT DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.permission_code IN (
            'decoration.view',
            'decoration.todo.view',
            'decoration.deposit_confirm',
            'decoration.settlement',
            'decoration.refund_confirm'
        )
        WHERE r.role_code = 'decoration_finance'
        ON CONFLICT DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.permission_code IN (
            'decoration.view',
            'decoration.todo.view'
        )
        WHERE r.role_code = 'decoration_security'
        ON CONFLICT DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.permission_code IN (
            'decoration.view',
            'decoration.create',
            'decoration.edit',
            'decoration.submit',
            'decoration.todo.view',
            'decoration.property_review',
            'decoration.leader_approve',
            'decoration.deposit_confirm',
            'decoration.entry_confirm',
            'decoration.acceptance',
            'decoration.settlement',
            'decoration.refund_approve',
            'decoration.refund_confirm',
            'decoration.cancel'
        )
        WHERE r.role_code = 'decoration_admin'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id
            FROM permissions
            WHERE permission_code LIKE 'decoration.%'
        );
        """
    )
    op.execute("DELETE FROM permissions WHERE permission_code LIKE 'decoration.%';")
    op.execute(
        """
        DELETE FROM roles
        WHERE role_code IN (
            'decoration_applicant',
            'decoration_property',
            'decoration_leader',
            'decoration_finance',
            'decoration_security',
            'decoration_admin'
        );
        """
    )

    op.drop_index("ix_decoration_refunds_project_id", table_name="decoration_refunds")
    op.drop_table("decoration_refunds")
    op.drop_index("ix_decoration_settlements_project_id", table_name="decoration_settlements")
    op.drop_table("decoration_settlements")
    op.drop_index("ix_decoration_acceptances_project_id", table_name="decoration_acceptances")
    op.drop_table("decoration_acceptances")
    op.drop_index("ix_decoration_entry_confirms_project_id", table_name="decoration_entry_confirms")
    op.drop_table("decoration_entry_confirms")
    op.drop_index("ix_decoration_deposit_confirms_project_id", table_name="decoration_deposit_confirms")
    op.drop_table("decoration_deposit_confirms")
    op.drop_index("ix_decoration_property_reviews_project_id", table_name="decoration_property_reviews")
    op.drop_table("decoration_property_reviews")
    op.drop_index("ix_workflow_actions_actor_user_id", table_name="workflow_actions")
    op.drop_index("ix_workflow_actions_instance_id", table_name="workflow_actions")
    op.drop_table("workflow_actions")
    op.drop_index("ix_workflow_instance_nodes_assignee_status", table_name="workflow_instance_nodes")
    op.drop_index("ix_workflow_instance_nodes_instance_id", table_name="workflow_instance_nodes")
    op.drop_table("workflow_instance_nodes")
    op.drop_constraint("fk_decoration_projects_current_workflow_instance_id", "decoration_projects", type_="foreignkey")
    op.drop_index("ix_workflow_instances_status", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_current_assignee", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_project_id", table_name="workflow_instances")
    op.drop_table("workflow_instances")
    op.drop_table("workflow_template_nodes")
    op.drop_index("ix_decoration_attachments_type", table_name="decoration_attachments")
    op.drop_index("ix_decoration_attachments_project_id", table_name="decoration_attachments")
    op.drop_table("decoration_attachments")
    op.drop_index("ix_decoration_project_spaces_business_unit_id", table_name="decoration_project_spaces")
    op.drop_index("ix_decoration_project_spaces_hall_id", table_name="decoration_project_spaces")
    op.drop_index("ix_decoration_project_spaces_project_id", table_name="decoration_project_spaces")
    op.drop_table("decoration_project_spaces")
    op.drop_index("ix_decoration_projects_planned_entry_date", table_name="decoration_projects")
    op.drop_index("ix_decoration_projects_current_assignee", table_name="decoration_projects")
    op.drop_index("ix_decoration_projects_applicant", table_name="decoration_projects")
    op.drop_index("ix_decoration_projects_store_status", table_name="decoration_projects")
    op.drop_table("decoration_projects")
    op.drop_table("workflow_templates")
