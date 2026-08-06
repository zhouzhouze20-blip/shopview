"""create Fuji revenue ODS landing tables

Revision ID: w1e2f3a4b5c6
Revises: v0d1e2f3a4b5
Create Date: 2026-08-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "w1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "v0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _loaded_at() -> sa.Column:
    return sa.Column(
        "source_loaded_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        comment="PAPI extraction time for the latest source version",
    )


def upgrade() -> None:
    op.create_table(
        "erp_supsetcharge",
        sa.Column("sscbillno", sa.String(100), nullable=False),
        sa.Column("sscrowno", sa.Numeric(12, 0), nullable=False),
        sa.Column("sscdjbh", sa.String(100)),
        sa.Column("ssctype", sa.String(1)),
        sa.Column("sscflag", sa.String(1)),
        sa.Column("sscsupid", sa.String(100)),
        sa.Column("sscwmid", sa.String(10)),
        sa.Column("sscmarket", sa.String(100)),
        sa.Column("sscmfid", sa.String(100)),
        sa.Column("sscdate", sa.DateTime()),
        sa.Column("sscfsdate", sa.DateTime()),
        sa.Column("sscfsmon", sa.String(6)),
        sa.Column("sscid", sa.String(2)),
        sa.Column("sscname", sa.String(100)),
        sa.Column("sscmoney", sa.Numeric(18, 2)),
        sa.Column("sscjsno", sa.String(100)),
        sa.Column("ssccontno", sa.String(100)),
        sa.Column("inputor", sa.String(100)),
        sa.Column("inputdate", sa.DateTime()),
        sa.Column("auditor", sa.String(100)),
        sa.Column("auditdate", sa.DateTime()),
        sa.Column("person1", sa.String(100)),
        sa.Column("sscmemo", sa.Text()),
        sa.Column("sscgdmoney", sa.Numeric(18, 2)),
        sa.Column("sscret", sa.String(1)),
        sa.Column("sscretdate", sa.DateTime()),
        sa.Column("sscretstatus", sa.String(1)),
        sa.Column("sscretmoney", sa.Numeric(18, 2)),
        sa.Column("sscfsstartdate", sa.DateTime()),
        sa.Column("sscfsenddate", sa.DateTime()),
        sa.Column("sscpayer", sa.String(100)),
        sa.Column("sscpaydate", sa.DateTime()),
        sa.Column("sscisqs", sa.String(1)),
        sa.Column("sscqssettleno", sa.String(100)),
        sa.Column("sscpaybillno", sa.String(100)),
        _loaded_at(),
        sa.PrimaryKeyConstraint("sscbillno", "sscrowno", name="pk_ods_erp_supsetcharge"),
        schema="ods",
        comment="Fuji ERP supplier settlement charge rows; one row per source bill and row number",
    )
    op.create_index("ix_ods_supsetcharge_fee_month", "erp_supsetcharge", ["sscfsmon"], schema="ods")
    op.create_index("ix_ods_supsetcharge_group", "erp_supsetcharge", ["sscmarket", "sscmfid"], schema="ods")
    op.create_index("ix_ods_supsetcharge_settlement", "erp_supsetcharge", ["sscjsno", "sscmfid"], schema="ods")
    op.create_index("ix_ods_supsetcharge_inputdate", "erp_supsetcharge", ["inputdate"], schema="ods")

    op.create_table(
        "erp_paybatch",
        sa.Column("pbseq", sa.Numeric(18, 0), nullable=False),
        sa.Column("pbsupid", sa.String(100), nullable=False),
        sa.Column("pbwmid", sa.String(10), nullable=False),
        sa.Column("pbmkt", sa.String(100), nullable=False),
        sa.Column("pbmfid", sa.String(100), nullable=False),
        sa.Column("pbmcontno", sa.String(100), nullable=False),
        sa.Column("pbjsno", sa.String(100), nullable=False),
        sa.Column("pbbillno", sa.String(100), nullable=False),
        sa.Column("pbdjlb", sa.String(1), nullable=False),
        sa.Column("pbbilltype", sa.String(10), nullable=False),
        sa.Column("pbcontno", sa.String(100), nullable=False),
        sa.Column("pbjssdate", sa.DateTime()),
        sa.Column("pbjsedate", sa.DateTime()),
        sa.Column("pbxssr", sa.Numeric(18, 2)),
        sa.Column("pbkp", sa.Numeric(18, 2)),
        sa.Column("pbfy2", sa.Numeric(18, 2)),
        sa.Column("pbdate", sa.DateTime()),
        sa.Column("pbpaybillno", sa.String(100)),
        _loaded_at(),
        sa.PrimaryKeyConstraint(
            "pbseq", "pbsupid", "pbwmid", "pbmkt", "pbmfid", "pbmcontno",
            "pbjsno", "pbbillno", "pbdjlb", "pbbilltype", "pbcontno",
            name="pk_ods_erp_paybatch",
        ),
        schema="ods",
        comment="Fuji ERP settlement-to-payment bridge rows at the original PAYBATCH grain",
    )
    op.create_index("ix_ods_paybatch_settlement", "erp_paybatch", ["pbjsno", "pbmfid"], schema="ods")
    op.create_index("ix_ods_paybatch_payment", "erp_paybatch", ["pbpaybillno"], schema="ods")
    op.create_index("ix_ods_paybatch_date", "erp_paybatch", ["pbdate"], schema="ods")

    op.create_table(
        "erp_suppayhead",
        sa.Column("sphbillno", sa.String(100), primary_key=True),
        sa.Column("sphflag", sa.String(1)),
        sa.Column("sphsupid", sa.String(100)),
        sa.Column("sphmfid", sa.String(100)),
        sa.Column("sphmoney", sa.Numeric(18, 2)),
        sa.Column("sphmoneyupper", sa.String(200)),
        sa.Column("sphtaxno", sa.String(100)),
        sa.Column("sphbank", sa.String(200)),
        sa.Column("sphaccntno", sa.String(200)),
        sa.Column("sphmktbank", sa.String(200)),
        sa.Column("sphmktaccntno", sa.String(200)),
        sa.Column("sphmkttaxno", sa.String(100)),
        sa.Column("sphpaydate", sa.DateTime()),
        sa.Column("inputor", sa.String(100)),
        sa.Column("inputdate", sa.DateTime()),
        sa.Column("auditor", sa.String(100)),
        sa.Column("auditdate", sa.DateTime()),
        sa.Column("sphvc1", sa.String(100)),
        _loaded_at(),
        schema="ods",
        comment="Fuji ERP supplier payment document headers",
    )
    op.create_index("ix_ods_suppayhead_paydate", "erp_suppayhead", ["sphpaydate"], schema="ods")
    op.create_index("ix_ods_suppayhead_inputdate", "erp_suppayhead", ["inputdate"], schema="ods")

    op.create_table(
        "erp_supsettlehead",
        sa.Column("sshbillno", sa.String(100), primary_key=True),
        sa.Column("sshflag", sa.String(1)),
        sa.Column("sshwmid", sa.String(10)),
        sa.Column("sshdate", sa.DateTime()),
        sa.Column("sshlastdate", sa.DateTime()),
        sa.Column("sshthisdate", sa.DateTime()),
        sa.Column("sshlastye", sa.Numeric(18, 2)),
        sa.Column("sshthisye", sa.Numeric(18, 2)),
        sa.Column("sshyfkje", sa.Numeric(18, 2)),
        sa.Column("sshsetadj", sa.Numeric(18, 2)),
        sa.Column("paydate", sa.DateTime()),
        sa.Column("sshplanpaydate", sa.DateTime()),
        sa.Column("sshenddate", sa.DateTime()),
        sa.Column("inputor", sa.String(100)),
        sa.Column("inputdate", sa.DateTime()),
        sa.Column("auditor", sa.String(100)),
        sa.Column("auditdate", sa.DateTime()),
        _loaded_at(),
        schema="ods",
        comment="Fuji ERP supplier settlement document headers",
    )
    op.create_index("ix_ods_supsettlehead_date", "erp_supsettlehead", ["sshdate"], schema="ods")
    op.create_index("ix_ods_supsettlehead_inputdate", "erp_supsettlehead", ["inputdate"], schema="ods")

    op.create_table(
        "erp_codecharge",
        sa.Column("cccode", sa.String(2), primary_key=True),
        sa.Column("ccname", sa.String(100)),
        sa.Column("ccdeftype", sa.String(100)),
        sa.Column("cctstatus", sa.String(1)),
        sa.Column("ccflag", sa.String(1)),
        sa.Column("cctype", sa.String(100)),
        sa.Column("cctax", sa.String(1)),
        sa.Column("cciskp", sa.String(1)),
        sa.Column("ccnum3", sa.Numeric(12, 6)),
        _loaded_at(),
        schema="ods",
        comment="Fuji ERP charge item dictionary and source tax rate",
    )

    op.create_table(
        "erp_manaframe",
        sa.Column("mfcode", sa.String(20), primary_key=True),
        sa.Column("mfcname", sa.String(100)),
        sa.Column("mffcode", sa.String(20)),
        sa.Column("mfpcode", sa.String(20)),
        sa.Column("mfcatcode", sa.String(20)),
        sa.Column("mfstatus", sa.String(1)),
        sa.Column("mftypecode", sa.String(1)),
        sa.Column("mfsubco", sa.String(20)),
        sa.Column("mfcatgroup", sa.String(10)),
        sa.Column("mfyt", sa.String(2)),
        sa.Column("mfkind", sa.String(2)),
        sa.Column("mfsource", sa.String(1)),
        sa.Column("mflast_modified", sa.DateTime()),
        _loaded_at(),
        schema="ods",
        comment="Fuji ERP management frame and source group dictionary",
    )
    op.create_index("ix_ods_manaframe_parent", "erp_manaframe", ["mfpcode"], schema="ods")
    op.create_index("ix_ods_manaframe_modified", "erp_manaframe", ["mflast_modified"], schema="ods")

    op.create_table(
        "erp_supplierbase",
        sa.Column("sbid", sa.String(20), primary_key=True),
        sa.Column("sbcname", sa.String(200)),
        sa.Column("sbsname", sa.String(100)),
        sa.Column("sbstatus", sa.String(1)),
        sa.Column("sbtaxno", sa.String(100)),
        sa.Column("sbbank", sa.String(200)),
        sa.Column("sbaccntno", sa.String(200)),
        sa.Column("sblxr", sa.String(100)),
        sa.Column("sblxfs", sa.String(100)),
        sa.Column("sbaddr", sa.String(500)),
        sa.Column("sbemail", sa.String(200)),
        _loaded_at(),
        schema="ods",
        comment="Fuji ERP supplier master data used by revenue reconciliation",
    )


def downgrade() -> None:
    op.drop_table("erp_supplierbase", schema="ods")
    op.drop_index("ix_ods_manaframe_modified", table_name="erp_manaframe", schema="ods")
    op.drop_index("ix_ods_manaframe_parent", table_name="erp_manaframe", schema="ods")
    op.drop_table("erp_manaframe", schema="ods")
    op.drop_table("erp_codecharge", schema="ods")
    op.drop_index("ix_ods_supsettlehead_inputdate", table_name="erp_supsettlehead", schema="ods")
    op.drop_index("ix_ods_supsettlehead_date", table_name="erp_supsettlehead", schema="ods")
    op.drop_table("erp_supsettlehead", schema="ods")
    op.drop_index("ix_ods_suppayhead_inputdate", table_name="erp_suppayhead", schema="ods")
    op.drop_index("ix_ods_suppayhead_paydate", table_name="erp_suppayhead", schema="ods")
    op.drop_table("erp_suppayhead", schema="ods")
    op.drop_index("ix_ods_paybatch_date", table_name="erp_paybatch", schema="ods")
    op.drop_index("ix_ods_paybatch_payment", table_name="erp_paybatch", schema="ods")
    op.drop_index("ix_ods_paybatch_settlement", table_name="erp_paybatch", schema="ods")
    op.drop_table("erp_paybatch", schema="ods")
    op.drop_index("ix_ods_supsetcharge_inputdate", table_name="erp_supsetcharge", schema="ods")
    op.drop_index("ix_ods_supsetcharge_settlement", table_name="erp_supsetcharge", schema="ods")
    op.drop_index("ix_ods_supsetcharge_group", table_name="erp_supsetcharge", schema="ods")
    op.drop_index("ix_ods_supsetcharge_fee_month", table_name="erp_supsetcharge", schema="ods")
    op.drop_table("erp_supsetcharge", schema="ods")
