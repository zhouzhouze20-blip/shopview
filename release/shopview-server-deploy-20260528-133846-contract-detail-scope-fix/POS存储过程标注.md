# POS 存储过程检索标注

检索目录：`建表/POS`

检索口径：

- 目录内共有 `34` 个 `.txt` 文件。
- 文件内容均为 Oracle `CREATE OR REPLACE PACKAGE BODY` 包体，未发现独立的 `CREATE PROCEDURE` 文件。
- 包体内共检出 `106` 个 `Procedure`、`22` 个 `Function`。下表将 `Procedure` 作为主要存储过程标注，`Function` 作为辅助函数一并列出。

## 业务域标注

| 业务域 | 包体文件 | 标注 |
| --- | --- | --- |
| POS 基础资料下发 | `JAVA_CREATEGOODS*`, `JAVA_GETGOODS*`, `JAVA_GETMENUINFO`, `JAVA_GETOPERROLE`, `JAVA_CREATEOPERUSER`, `JAVA_GETSYJ*`, `MOB_*` | 给 POS/JAVA/移动端提供商品、单位、价格、促销、角色、菜单、收银机范围、付款方式、系统参数等查询结果集。 |
| 促销/优惠接口 | `JAVA_CREATEGOODSPOP`, `JAVA_GETYHINFOLIST`, `JAVA_GETBARCODEGIFT`, `JAVA_GETpopinfo`, `popinterface` | 查询或计算促销、赠品、优惠券/退货扣回券相关数据。 |
| 销售导入/上传 | `Saleimp`, `Saleimpinterface`, `Improtsaleinterface`, `Sellimp` | 处理第三方/接口销售数据校验、生成销售单、上传总部、合同销售导入审批。 |
| 退货/换货/CRM 回写 | `Htth`, `Java_Getbackgoodsinfo` | 处理换货退货、生成 POS/CRM 单据、卡券校验、取消、日取消以及退货商品明细查询。 |
| 卡支付/会员支付拆分 | `CardCRM_POS`, `Cardcrm_Payment` | 处理储值卡/会员卡支付、支付分摊、POS 卡支付汇总、同步 `cardpayment`。 |
| POS 日初始化/调度 | `posdayinit` | POS 日初始化、清理日志/过期促销、重置收银机状态、提交定时任务。 |
| 文件导入 | `Sysfileimport` | 文件导入主表、日志、结束状态维护。 |
| 数据库监控维护 | `DB_Monitor` | 表空间、对象分析、无效对象编译、分区维护、空间日志、DB job 调度。 |

## 明细清单

| 文件/包体 | 过程标注 | 辅助函数 | 关键表/依赖 |
| --- | --- | --- | --- |
| `CardCRM_POS.txt` / `CardCRM_POS` | `Sp_Build_PosCardPay`(60, 106)：按日期或日期范围生成 POS 卡支付汇总；`sp_sendpay_day`(131)：按日同步卡支付；`SubmitPay`(163, 171)：提交任务。 | `f_GetPosPara`(7)：取 POS 参数；`f_PayModeIsMzk`(25)：判断付款方式是否面值卡。 | `dbusrposnew.syspara`, `sellhead`, `sellpayment`, `paymode`, `poscardpay`, `cardpayment` |
| `Cardcrm_Payment.txt` / `Cardcrm_Payment` | `Split`(27)：拆分销售付款到商品支付分摊；`Getpayfd`(528)：获取付款分担信息。 | `f_CanZL`(8)：判断付款行是否找零行；`f_Isdzqpay`(515)：判断是否电子券付款。 | `sellhead`, `selldetail`, `sellpayment`, `sellpaygoods`, `paymode`, `dbusrpop.tktqtype@gpp`, `crmjflog`, `tktsellfqamt` |
| `DB_Monitor.txt` / `DB_Monitor` | `P___Public`(5)：分段占位；`GetCPUCount`(9)：读取 CPU 数；`AddMessage`(17)：写监控消息；`P___Daily_Operation`(40)：日常维护占位；`Sp_Sys_Analyze_Object`(44)：对象统计分析；`Sp_Sys_Check_TableSpace`(63)：表空间检查；`Sp_Sys_Check_Tables`(147)：表检查；`Sp_Sys_Check_Jobs`(152)：job 检查；`CompileInvalidObjects`(177)：编译无效对象；`CompileAllInvalidObjects`(216)：全用户无效对象编译；`P___Partitions`(229)：分区维护占位；`Check_Partition`(289)：检查并补分区；`Schedule_Partition`(364)：调度分区维护；`sp_SaveSpaceLog`(448)：保存空间日志；`P___Interface`(488)：接口占位；`Submit`(492)：提交监控 job；`Job_Submit`(512)：创建 job。 | `GetPartitionKeyColumn`(233)；`GetTablePartitionType`(259)；`GetSubPartitionTemplate`(278)。 | `v$parameter`, `v$instance`, `dba_*`, `all_objects`, `all_users`, `all_tab_partitions`, `gatherspacelog`, `dbms_job` |
| `Htth.txt` / `Htth` | `Sp_Htthougtpay`(147)：换退货付款生成；`Htthpayment`(464)：换退货付款处理；`Htthnew`(845)：新建换退货单；`Genpossellbill`(1350)：生成 POS 销售单；`Gencrmbill`(1594)：生成 CRM 单；`Checkkh`(1850)：卡号/客户校验；`Checkispapercoupon`(1980)：纸券判断；`Checkcard`(2000)：卡校验；`Checktranscard`(2012)：转换卡号；`Checkcardtrack`(2020)：卡轨迹校验；`Bapprove`(2072)：换退货审批主流程；`Approve`(2895)：审批入口；`Cancel`(2909)：取消；`Daycancel`(2981)：按日取消。 | `f_Getstringpara`(8)；`f_Gethgstring`(40)；`f_Isdzq`(68)；`Fgetthkhzxl`(79)；`Fgetoriginalinv_Hh`(92)。 | `sellhead`, `selldetail`, `sellpayment`, `sellpaygoods`, `htthsellhead`, `htthselldetail`, `htthsellpayment`, `htthsellpaygoods`, `dbusrposnew.salehead`, `dbusrposnew.salegoods`, `dbusrposnew.salepay`, `sellhead_crm`, `selldetail_crm`, `sellpayment_crm`, `tktcardfqtotal`, `mzgiftselldetailhtth` |
| `Improtsaleinterface.txt` / `Improtsaleinterface` | `Raiseerr`(10)：统一抛错回滚；`Checkglobparm`(26)：全局参数检查；`Initsalehead`(39)：初始化销售主表行；`Insertsalehead`(100)：写销售主表；`Initsalegoods`(141)：初始化销售明细；`Insertsalegoods`(232)：写销售明细；`Initsalepay`(301)：初始化付款；`Insertsalepay`(331)：写付款；`Insertsellmail`(365)：写销售邮件/队列；`Checkbill`(379)：检查小票；`Insertsaleok`(384)：标记销售完成。 | `Getsalebillno`(16)：取销售单号。 | `dbusrposnew.seq_salehead`, `dbusrposnew.salehead`, `dbusrposnew.salegoods`, `dbusrposnew.salepay`, `manaframe`, `goodsbase`, `goodsmframe`, `pospaymode`, `sellmail` |
| `JAVA_CREATECRMVIPZK.txt` / `JAVA_CREATECRMVIPZK` | `CREATECRMVIPZK`(5)：下发 CRM 会员折扣/批量价格优惠。 | 无 | `posgoodsamount` |
| `JAVA_CREATECUSTOMERGROUP.txt` / `JAVA_CREATECUSTOMERGROUP` | `CREATECUSTOMERGROUP`(5)：下发会员分组静态数据。 | 无 | `dual` |
| `JAVA_CREATEGOODS.txt` / `JAVA_CREATEGOODS` | `CREATEGOODS`(5)：下发全量 POS 商品基础资料。 | 无 | `posgoods`, `Fchkgoodsiszt` |
| `JAVA_CREATEGOODSAMOUNT.txt` / `JAVA_CREATEGOODSAMOUNT` | `CREATEGOODSAMOUNT`(4)：下发商品批量价格/折上折数据。 | 无 | `posgoodsamount` |
| `JAVA_CREATEGOODSPOP.txt` / `JAVA_CREATEGOODSPOP` | `CREATEGOODSPOP`(5)：下发有效促销商品规则。 | 无 | `pospopinfo` |
| `JAVA_CREATEGOODSSUNITS.txt` / `JAVA_CREATEGOODSSUNITS` | `CREATEGOODSSUNITS`(5)：下发商品多单位资料。 | 无 | `posgoodsunits` |
| `JAVA_CREATEOPERUSER.txt` / `JAVA_CREATEOPERUSER` | `CREATEOPERUSER`(5)：下发 POS 操作员账号。 | 无 | `posoperaccnt`, `java_password` |
| `JAVA_GETBARCODEGIFT.txt` / `JAVA_GETBARCODEGIFT` | `GETBARCODEGIFT`(7)：按优惠单号查询条码赠品促销。 | 无 | `pospopinfo` |
| `JAVA_GETBUYERINFO.txt` / `JAVA_GETBUYERINFO` | `GETBUYERINFO`(5)：查询客户/购买方资料。 | 无 | `poscustinfo` |
| `JAVA_GETCHILDGOODSLIST.txt` / `JAVA_GETCHILDGOODSLIST` | `GETCHILDGOODSLIST`(5)：按分析码/柜组/类型查询子商品。 | 无 | `posgoods` |
| `JAVA_GETGOODSAMOUNTINFOLIST.txt` / `JAVA_GETGOODSAMOUNTINFOLIST` | `GETGOODSAMOUNTINFOLIST`(5)：按商品/柜组/单位查询批量价格。 | 无 | `posgoodsamount` |
| `JAVA_GETGOODSINFOLIST.txt` / `JAVA_GETGOODSINFOLIST` | `GETGOODSINFOLIST`(11)：按条码/商品编码/分析码查询商品明细。 | 无 | `posgoods`, `fGetStock` |
| `JAVA_GETGOODSSUNITSLIST.txt` / `JAVA_GETGOODSSUNITSLIST` | `GETGOODSSUNITSLIST`(5)：按商品查询多单位列表。 | 无 | `posgoodsunits` |
| `JAVA_GETMENUINFO.txt` / `JAVA_GETMENUINFO` | `GETMENUINFO`(5)：下发 POS 菜单功能。 | 无 | `posfunction` |
| `JAVA_GETOPERROLE.txt` / `JAVA_GETOPERROLE` | `GETOPERROLE`(5)：下发操作角色、权限、折扣限额和授权范围。 | 无 | `posoperrole`, `java_fmergerolerange` |
| `JAVA_GETPOSCALL.txt` / `JAVA_GETPOSCALL` | `GETPOSCALL`(5)：下发 POS 呼叫文本。 | 无 | `poscall` |
| `JAVA_GETSYJPAYMODE.txt` / `JAVA_GETSYJPAYMODE` | `GETSYJPAYMODE`(5)：按收银机查询付款方式模板。 | 无 | `pospaytemplet`, `pospaymode`, `syjmain` |
| `JAVA_GETSYJRANGE.txt` / `JAVA_GETSYJRANGE` | `GETSYJRANGE`(5)：按收银机查询可售柜组范围。 | 无 | `syjgrange`, `syjmain` |
| `JAVA_GETYHINFOLIST.txt` / `JAVA_GETYHINFOLIST` | `GETYHINFOLIST`(8)：按商品、柜组、品类、品牌、规格查询优惠规则。 | 无 | `pospopinfo` |
| `JAVA_GETpopinfo.txt` / `JAVA_GETpopinfo` | `GETpopinfo`(3)：按门店/经营单位/优惠单号查询促销信息。 | 无 | `dbusrpop.pospopinfo_r` |
| `Java_Getbackgoodsinfo.txt` / `Java_Getbackgoodsinfo` | `Getbackgoodsinfo`(8)：按原小票和商品条件查询退货商品明细。 | 无 | `selldetail`, `sellhead` |
| `MOB_GETPAYMODE.txt` / `MOB_GETPAYMODE` | `GETPAYMODE`(5)：移动端获取终端付款方式。 | 无 | `pospaytemplet`, `pospaymode`, `syjmain` |
| `MOB_GETSYSPARA.txt` / `MOB_GETSYSPARA` | `GETSYSPARA`(5)：移动端获取系统参数。 | 无 | `posprivatepara` |
| `Saleimp.txt` / `Saleimp` | `Raiseerr`(3)：统一抛错回滚；`Upload_Invno`(32)：上传单表销售数据；`Sp_Gensale`(141, 186)：生成销售单；`Sp_Gethqimp`(226)：获取总部导入数据；`Submit`(276)：提交任务；`Job_Submit`(282)：创建 job。 | `f_GetPaymode`(9)：按类型取默认付款方式。 | `dbusrpos.pospaymode`, `saleinfo_temp`, `manaframe`, `goodsbase`, `goodsmframe`, `interfacelog`, `dbusrdif.saleinfo_temp@sys`, `dbms_job` |
| `Saleimpinterface.txt` / `Saleimpinterface` | `Raiseerr`(16)：统一抛错回滚；`Checkisdoc`(42)：检查接口单据/基础资料；`Checkpaycode`(119)：校验付款代码；`Checkimpmainrow_Ex`(132)：外部主表行校验；`Checkimpmainrow`(174)：主表行校验；`Sp_Checkimportmain`(224)：检查导入主表；`Checkimpdetrow`(237)：明细行校验；`Sp_Checkimprotdet`(281)：检查导入明细；`Checkimppayrow`(293)：付款行校验；`Sp_Checkimportpay`(336)：检查导入付款；`p___________Gensale`(347)：生成销售分隔占位；`Sp_Checksalebill`(352)：销售单整体校验；`Sp_Gensalebill`(416)：生成销售单；`Sp_Deal_Lssal`(536)：处理临时销售导入。 | `Fgetsyjid`(11)；`Fgetdjlb`(22)；`Fgetpaymodeconver`(31)。 | `ls_sal_main`, `ls_sal_detail`, `ls_sal_pay`, `manaframe`, `supplierbase`, `goodsbase`, `goodsmframe`, `pospaymode`, `paymodeconver`, `interfacelog` |
| `Sellimp.txt` / `Sellimp` | `Raiseerr`(5)：统一抛错回滚；`Approve4pl`(53)：批量审批合同销售导入；`Approve4one`(343)：单笔审批；`Approve`(458)：审批入口。 | `Fgetpaycode`(11)：付款方式转换；`Fgetpayyy`(34)：取付款方式是否溢余；`Fgetpaycodename`(41)：取付款方式名称。 | `paymodeconver_bd`, `paymode`, `pos_sellhthead`, `pos_sellhtdet`, `pos_sellhtpay`, `sellpayment`, `dbusrmall.manapara@sys` |
| `Sysfileimport.txt` / `Sysfileimport` | `Sp_Startimport`(15)：开始导入并写主记录；`Sp_Importlog`(30)：写接口日志；`Sp_Endimport`(56)：结束导入并更新状态。 | `Fgetseqno`(4)：取导入序号。 | `seq_importfile`, `sys_file_import_master`, `interfacelog`, `sys_file_import_dbconfig` |
| `popinterface.txt` / `popinterface` | 无 | `fgetthkhzxl`(3)：获取退货扣回券折现比率。 | `tktqtype` |
| `posdayinit.txt` / `posdayinit` | `init`(7)：初始化系统日期/地点/ID；`exec_initdata`(15)：执行日初始化；`submit`(68)：提交初始化任务；`run`(107)：运行入口；`job_submit`(115)：创建定时任务；`job_remove`(129)：移除任务。 | 无 | `syjmain`, `posoperlog`, `posopererrors`, `posinfo`, `pospopinfo`, `posgoodsamount`, `opererrors`, `dbusrposnew.syjcmdmail`, `debug_log`, `dbms_job` |

## 后续建议

- 如果要迁移到新系统，建议先从 `JAVA_*` 和 `MOB_*` 这类只读结果集接口入手，风险最低。
- `Htth`, `Cardcrm_Payment`, `Saleimpinterface`, `Sellimp` 都包含复杂写入和跨库依赖，迁移前需要补充真实调用入口、事务边界和样例单据。
- 当前目录只有包体，缺少 package specification。若 ERP 库中能导出包头，可以进一步区分“对外公开过程”和“包内私有过程/函数”。
