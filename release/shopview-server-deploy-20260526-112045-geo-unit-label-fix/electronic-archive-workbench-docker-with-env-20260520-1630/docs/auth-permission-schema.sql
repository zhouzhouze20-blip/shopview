-- 用户、权限、数据范围、企微登录基础表
-- 执行用户：建议使用 ETLKP，或将 ETLKP. 前缀替换为实际 schema。

create table ETLKP.EA_USER (
  id varchar2(64) primary key,
  username varchar2(100) not null,
  display_name varchar2(100),
  mobile varchar2(50),
  email varchar2(200),
  wecom_user_id varchar2(100),
  department_name varchar2(200),
  status varchar2(20) default 'enabled',
  last_login_time date,
  is_deleted varchar2(1) default '0',
  create_time date default sysdate,
  update_time date default sysdate
);

create unique index ETLKP.UK_EA_USER_USERNAME on ETLKP.EA_USER(username);
create index ETLKP.IDX_EA_USER_WECOM on ETLKP.EA_USER(wecom_user_id);

create table ETLKP.EA_ROLE (
  id varchar2(64) primary key,
  role_code varchar2(100) not null,
  role_name varchar2(100) not null,
  description varchar2(500),
  is_deleted varchar2(1) default '0',
  create_time date default sysdate,
  update_time date default sysdate
);

create unique index ETLKP.UK_EA_ROLE_CODE on ETLKP.EA_ROLE(role_code);

create table ETLKP.EA_PERMISSION (
  id varchar2(64) primary key,
  permission_code varchar2(150) not null,
  permission_name varchar2(150) not null,
  permission_type varchar2(30) default 'menu',
  route_path varchar2(300),
  parent_code varchar2(150),
  sort_no number default 0,
  is_deleted varchar2(1) default '0',
  create_time date default sysdate,
  update_time date default sysdate
);

create unique index ETLKP.UK_EA_PERMISSION_CODE on ETLKP.EA_PERMISSION(permission_code);

create table ETLKP.EA_USER_ROLE (
  id varchar2(64) primary key,
  user_id varchar2(64) not null,
  role_id varchar2(64) not null,
  is_deleted varchar2(1) default '0',
  create_time date default sysdate,
  update_time date default sysdate
);

create index ETLKP.IDX_EA_USER_ROLE_USER on ETLKP.EA_USER_ROLE(user_id);
create index ETLKP.IDX_EA_USER_ROLE_ROLE on ETLKP.EA_USER_ROLE(role_id);

create table ETLKP.EA_ROLE_PERMISSION (
  id varchar2(64) primary key,
  role_id varchar2(64) not null,
  permission_id varchar2(64) not null,
  is_deleted varchar2(1) default '0',
  create_time date default sysdate,
  update_time date default sysdate
);

create index ETLKP.IDX_EA_ROLE_PERMISSION_ROLE on ETLKP.EA_ROLE_PERMISSION(role_id);

create table ETLKP.EA_DATA_SCOPE (
  id varchar2(64) primary key,
  scope_code varchar2(100) not null,
  scope_name varchar2(150) not null,
  scope_type varchar2(30) default 'store',
  store_ids varchar2(2000),
  store_names varchar2(4000),
  is_deleted varchar2(1) default '0',
  create_time date default sysdate,
  update_time date default sysdate
);

create unique index ETLKP.UK_EA_DATA_SCOPE_CODE on ETLKP.EA_DATA_SCOPE(scope_code);

create table ETLKP.EA_USER_DATA_SCOPE (
  id varchar2(64) primary key,
  user_id varchar2(64) not null,
  scope_id varchar2(64) not null,
  is_deleted varchar2(1) default '0',
  create_time date default sysdate,
  update_time date default sysdate
);

create index ETLKP.IDX_EA_USER_SCOPE_USER on ETLKP.EA_USER_DATA_SCOPE(user_id);

create table ETLKP.EA_AUTH_SESSION (
  id varchar2(64) primary key,
  user_id varchar2(64) not null,
  expires_at date not null,
  is_deleted varchar2(1) default '0',
  create_time date default sysdate,
  update_time date default sysdate
);

create index ETLKP.IDX_EA_SESSION_USER on ETLKP.EA_AUTH_SESSION(user_id);
create index ETLKP.IDX_EA_SESSION_EXPIRES on ETLKP.EA_AUTH_SESSION(expires_at);

create table ETLKP.EA_USER_PASSWORD (
  id varchar2(64) primary key,
  user_id varchar2(64) not null,
  password_hash varchar2(300) not null,
  password_reset_required varchar2(1) default '1',
  is_deleted varchar2(1) default '0',
  create_time date default sysdate,
  update_time date default sysdate
);

create unique index ETLKP.UK_EA_USER_PASSWORD_USER on ETLKP.EA_USER_PASSWORD(user_id);

insert into ETLKP.EA_ROLE (id, role_code, role_name, description)
values (rawtohex(sys_guid()), 'admin', '系统管理员', '拥有全部管理权限');

insert into ETLKP.EA_PERMISSION (id, permission_code, permission_name, permission_type, route_path, sort_no)
values (rawtohex(sys_guid()), 'admin.users', '用户管理', 'menu', '/admin/users', 900);

insert into ETLKP.EA_PERMISSION (id, permission_code, permission_name, permission_type, route_path, sort_no)
values (rawtohex(sys_guid()), 'admin.permissions', '权限管理', 'menu', '/admin/permissions', 910);

insert into ETLKP.EA_PERMISSION (id, permission_code, permission_name, permission_type, route_path, sort_no)
values (rawtohex(sys_guid()), 'admin.dataScopes', '数据范围管理', 'menu', '/admin/data-scopes', 920);

commit;
