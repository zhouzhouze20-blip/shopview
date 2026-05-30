create table ETLKP.MANUAL_BUSINESS_BILL (
  id varchar2(64) primary key,
  doc_no varchar2(100) not null,
  doc_source varchar2(50) default '手工补录' not null,
  business_date date not null,
  partner_name varchar2(300) not null,
  store_name varchar2(300),
  department_name varchar2(300),
  business_type varchar2(100),
  amount number(18, 2) not null,
  remark varchar2(1000),
  created_by varchar2(100),
  is_deleted varchar2(1) default '0' not null,
  create_time date default sysdate not null,
  update_time date default sysdate not null
);

create unique index ETLKP.UK_MANUAL_BUSINESS_BILL_NO
  on ETLKP.MANUAL_BUSINESS_BILL(doc_no);

comment on table ETLKP.MANUAL_BUSINESS_BILL is '财务手工补录业务单据，用于无 OA/付款单来源的发票关联';
comment on column ETLKP.MANUAL_BUSINESS_BILL.id is '手工补录单据 ID';
comment on column ETLKP.MANUAL_BUSINESS_BILL.doc_no is '手工补录单据编号';
comment on column ETLKP.MANUAL_BUSINESS_BILL.doc_source is '单据来源，默认手工补录';
comment on column ETLKP.MANUAL_BUSINESS_BILL.business_date is '业务单据日期';
comment on column ETLKP.MANUAL_BUSINESS_BILL.partner_name is '供应商/往来方';
comment on column ETLKP.MANUAL_BUSINESS_BILL.store_name is '门店/购方';
comment on column ETLKP.MANUAL_BUSINESS_BILL.department_name is '所属部门';
comment on column ETLKP.MANUAL_BUSINESS_BILL.business_type is '业务类型';
comment on column ETLKP.MANUAL_BUSINESS_BILL.amount is '单据金额';
