"""Build a bounded, source-backed readiness report and evidence notebook.

No database calls. Reads this run's saved aggregate evidence only.
"""
import json
from decimal import Decimal
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent / 'coupon-data-audit-20260905'


def evidence(label):
    return json.loads((BASE / (label + '.json')).read_text())


def rows(label):
    data = evidence(label)
    assert 'error_type' not in data, label
    assert not data['result'].get('truncated'), label
    return data['result']['rows']


def build():
    pg = rows('pg_qixi_events')
    oracle = rows('gpp_source_qixi_counts')
    a = {(r['tcfljetype'],r['tcflzy']):(int(r['rows']), Decimal(r['signed_amount'])) for r in pg}
    b = {(r['TCFLJETYPE'],r['TCFLZY']):(int(r['ROWS_COUNT']), Decimal(str(r['SIGNED_AMOUNT']))) for r in oracle}
    assert a == b, 'Oracle/ODS counts or signed amounts differ'
    keys = evidence('cross_source_asset_keys')
    assert keys['intersection'] == keys['crm_record_rows'] == keys['pg_unique_asset_keys'] == 1925
    assert keys['crm_set_sha256'] == keys['pg_set_sha256']
    assert sum(r['rows'] for r in pg if r['tcflzy']=='M') == 1925
    assert sum(r['early_rows'] for r in pg if r['tcflzy']=='M') == 694
    history = rows('bi_qixi_member_history_compat')[0]
    assert sum(int(history[k]) for k in ('missing_history','one_history','overlapping_history')) == 828
    gaps = rows('bi_history_gap_context')
    assert sum(int(r['members']) for r in gaps)==46
    defs = {r['third_party_no']:r for r in rows('bi_selected_templates') if r['id'] in ('532623','532624','532625','532626')}
    chart_rows=[]
    for r in pg:
        if r['tcflzy']=='M':
            chart_rows.append({'coupon':r['tcfljetype'], 'name':defs[r['tcfljetype']]['name'], 'assets':r['assets'], 'early':r['early_rows'], 'early_rate':r['early_rows']/r['rows'], 'member_count':r['members'], 'issue_amount':float(r['signed_amount']), 'valid_start':'2026-08-14','valid_end':'2026-08-19'})
    chart_rows.sort(key=lambda r:r['early_rate'],reverse=True)
    sources=[]
    used_sources = [
        ('pg_qixi_events','七夕券日志及预发范围',['public.tktcardfqlog']),
        ('gpp_source_qixi_counts','GPP源库同口径复核',['DBUSRPOP.TKTCARDFQLOG']),
        ('pg_qixi_integrity','券资产及会员维表质量',['public.tktcardfqlog','public.fj_dw_member_dim']),
        ('pg_qixi_ticket_link','小票匹配及会员身份',['public.tktcardfqlog','public.salehead']),
        ('bi_selected_templates','CRM三类投放模板',['ferry_wadge.coupon_template']),
        ('bi_three_template_link','新人券及品牌券关联',['ferry_wadge.coupon_record_601','ferry_wadge.coupon_template','ferry_wadge.coupon_log']),
        ('bi_qixi_link','七夕CRM模板与日志关联',['ferry_wadge.coupon_record_601','ferry_wadge.coupon_template','ferry_wadge.coupon_log']),
        ('bi_newcomer_unlinked','新人券未关联记录分布',['ferry_wadge.coupon_record_601','ferry_wadge.coupon_log']),
        ('bi_member_identity','CRM会员身份桥接',['ferry_wadge.coupon_record_601','ferry_wadge.member','ferry_wadge.member_scenes']),
        ('bi_qixi_member_history_compat','活动开始时会员等级匹配',['ferry_wadge.member_level_track','ferry_wadge.member','ferry_wadge.coupon_record_601']),
        ('bi_history_gap_context','等级未匹配的注册时点',['ferry_wadge.member_level_track','ferry_wadge.member_scenes','ferry_wadge.member','ferry_wadge.coupon_record_601']),
        ('pg_freshness','ODS业务及加载截止时间',['public.tktcardfqlog','public.salehead','ods.crm_coupon_record_603','ods.campaign_rule_batches']),
        ('pg_crm_counts','本地CRM模板覆盖范围',['ods.crm_coupon_template_603']),
        ('bi_plan_missing_scope','CRM营销计划覆盖',['ferry_wadge.promotion_market_plan']),
        ('gpp_rule_types','实际ERP费用分摊类型',['DBUSRPOP.TKTGOODSFQFT']),
        ('gpp_rule_comments','ERP字段注释核对',['ALL_COL_COMMENTS']),
        ('bi_qixi_counter_semantics','CRM券状态分布',['ferry_wadge.coupon_record_601']),
    ]
    for label,title,tables in used_sources:
        e=evidence(label)
        sources.append({'id':label,'label':title,'query':{'engine':'PostgreSQL' if e['source']=='pg' else ('MySQL via PAPI' if e['source']=='14' else 'Oracle via PAPI'),'language':'SQL','sql':e['sql'],'executed_at':e.get('finished_at',e['started_at']),'tables_used':tables,'description':title,'filters':['具体范围、聚合及排除条件以所附执行SQL为准；未返回个人身份明细。']}})
    sources.append({'id':'asset_key_comparison','label':'CRM与ShopView券资产全集比对','query':{'description':'CRM按coupon_code稳定分页10页，与PostgreSQL资产集合逐键比较；只保存集合摘要和计数。两个集合均1925，交集1925，双方差集均0，SHA256一致。','tables_used':['ferry_wadge.coupon_record_601','ferry_wadge.coupon_template','public.tktcardfqlog'],'executed_at':keys['checked_at']}})
    blocks=[]
    def md(id,body,source=None):
        block={'id':id,'type':'markdown','body':body}
        if source: block['sourceId']=source
        blocks.append(block)
    md('title','# Coupon Data Readiness')
    md('summary','## Executive Summary\n\n- **推荐以项目ODS承载日常销售/券流水分析，以PAPI读取CRM投放与会员历史、ERP规则作为补充核验。** 本次真实数据支持统一投放主线，但尚未验证自动下发接口。\n- **七夕样本已打通模板—券资产—小票—会员。** 下一步优先补采CRM模板/记录及会员等级轨迹，不必从日期猜测活动归属。\n- **品牌券需要按兑现方式分流，结算与AI结论要设质量门槛。** 不带ERP编号的礼品/权益券不等于异常；费用规则的旧注释不能直接作为公式。')
    md('scope','## 核查范围与证据边界\n\n主体为601门店：中心新客券（2026）、七夕四券、海蓝之谜VIP悦享券，并用GIADA专享券检查非POS路径。另检查603门店本地CRM覆盖。成功查询主要采集于2026年9月5日12:50—12:56（北京时间），不是实时仪表盘。\n\n券资产数、流水笔数、会员人数和模板计数分别统计；核对范围是数据关联可行性，不是完整活动业绩或已确认结算金额。各源非跨库同一事务，进行中的计划可能在查询间变化。')
    md('freshness','## 本地ODS可做日常分析，但CRM覆盖不足\n\n本地券流水已到9月5日，销售记录到当日12:50；CRM发券记录最大源更新时间为8月31日01:00、最大加载时间为8月31日10:35。CRM模板与记录必须分别显示更新时间，不能把模板刷新成功当作记录也已刷新。\n\n**影响：近期投放分析应补查CRM数据；仅凭当前本地CRM记录会漏掉9月事件。** 最后事件日期只证明存在近期记录，不证明全部数据完整同步。','pg_freshness')
    md('crm_scope','### 本地模板不是全量CRM券库\n\n当前本地603模板共268条，全部标为gift；不能代表601的POS活动券、新人券已经同步。建议补采已确认的租户和类型范围，保留原始类型，不按券名字猜金额或路径。','pg_crm_counts')
    md('cross_keys','## 七夕模板与券资产可准确关联\n\nCRM模板532623、532624、532625、532626对应B/E/H/M。逐页读取并与ShopView独立比对后，两边均为1,925个资产键，全部相同，无单边遗漏。\n\n**实施方向：活动绑定CRM模板，发放记录通过第三方券编号、门店和券种连到券资产。** 这一核验结论针对七夕样本；不能直接外推所有历史模板。','asset_key_comparison')
    md('preissue','## 只按活动日期查发券，会漏掉694个资产\n\n本档1,925个发放资产中，694个在8月14日之前已发放，占36.1%；四类券的预发占比不同。相关2,699笔流水的活动编号全部为空或0。图中分母为各券发放资产，不是会员人数。\n\n**发放期、有效期、活动档期必须分开保存；日期只用于核验，不作为唯一归属键。**','pg_qixi_events')
    blocks.append({'id':'preissue_chart_block','type':'chart','chartId':'preissue_chart'})
    md('source_check','### 本次源库核对通过\n\nGPP源库和项目ODS按券种、动作分组的11组流水笔数及带符号金额一致；这是选定七夕范围的核对结果，不是全库同步验收。','gpp_source_qixi_counts')
    md('tickets','## 小票能连上，但持券人不能自动当作购买人\n\n711笔消费券流水、63笔退券流水均唯一匹配小票；这不是711张、63张去重小票。消费流水中452笔持券人与小票会员一致，11笔小票未登记会员，其余248笔身份不同。\n\n**会员本人消费与持券关联消费要分别展示。** 身份不一致是核查线索，不是违规结论；同票多券需要先去重再统计销售。','pg_qixi_ticket_link')
    md('types','## 新人券、品牌POS券和品牌权益券走不同路径\n\n三类样本的字段证明：长期计划和阶段计划都存在，而品牌券既可能进POS，也可能是独立权益。名称里的“500元”并不能证明数据库券面额就是500元。','bi_selected_templates')
    blocks.append({'id':'samples_table_block','type':'table','tableId':'samples_table'})
    md('sample_link','### 关联覆盖要按兑现路径解释\n\n中心新客券明细有14,440条，其中14,428条可关联CRM侧ERP日志；海蓝之谜6,425条全部可关联；GIADA的3,917条没有ERP编号，不能据此宣称发券失败或计算POS连带销售。\n\n这些是查询快照中的记录数，不等于确认有效发放人数，也不是不同类型投放的效果排名。','bi_three_template_link')
    md('newcomer_gap','### 新人券有12条历史待核记录\n\n未关联的12条新人券记录均缺第三方券编号，分布于2月至8月，并非都在当天刚发。原因尚未确认，应列为待核发放；不能只凭已创建记录判断ERP到账成功。','bi_newcomer_unlinked')
    md('history','## 活动前会员分层大部分可以还原\n\n828名获券会员中，782名在活动开始时可匹配一条等级有效记录，46名无匹配，未发现该时点重叠记录。有效区间采用本次查询的包含边界假设；正式实施还需核验等级边界语义。','bi_qixi_member_history_compat')
    md('history_context','### 46名无匹配并不等于46名数据丢失\n\n其中44名是在活动开始后才注册，属于新会员队列；另2名是此前注册会员，需要补查。\n\n**历史等级作为可用数据源纳入规划，并给新客单独分组；不要用当前等级覆盖过去。**','bi_history_gap_context')
    md('identity','### 身份链必须经过会员映射\n\n828个CRM获券会员ID全部能经member到member_scenes关联。直接把获券会员ID当member_scenes主键，只会碰到654条，且主键数值碰巧相同不证明同一人。应沿明确关系关联等级轨迹，并进一步核对会员卡号。','bi_member_identity')
    md('rules','## 费用规则存在，但不能照旧注释直接计算\n\nERP档期2205的分摊结果表查到474条规则，类型实际为A/B/C、计算方法为5，费率原值覆盖0—1。该表范围是ERP档期，尚未证明每条都适用于七夕四券，不能直接合计成四券费用。','gpp_rule_types')
    md('rules_caveat','### 旧字典与实际代码存在解释差异\n\n源库字段注释仍描述1/2/3对应销售额、返券额、收券额，与实际A/B/C不一致；仓库过程也可见按A/B/C拼接付款方式和券种。需要现行执行逻辑与费用结果样本共同核对，才能确定供应商分摊公式。\n\n**本轮不出供应商应扣金额。** 在费用表按名称含“券/促销/活动”检索无结果，不能据此认定没有扣费。','gpp_rule_comments')
    md('counter','## AI不能混用模板计数、使用状态和交易流水\n\n以E券为例，模板计数、当前状态和消费流水是不同对象：模板核销计数401，当前used_status=1的记录377，而消费动作O有406笔。三者不相等，不能在未核验语义时选其中一个当“核销人数”。\n\nAI数据包应使用后端明确计算的发放资产、去重使用会员、消费/退券流水与净金额；模板计数仅作核对参考。此差异是计数口径待核，不自动认定数据库错误。')
    md('next','## 建议的建设顺序\n\n1. **先补数据基础：** 按门店采集CRM模板、发放记录、会员映射和等级轨迹；保存加载时间、来源主键和规则版本，保留失败/未知发放。\n2. **再做统一投放与经营分析：** 长期新人计划、专项活动、品牌阶段共享投放模型；POS券与礼品权益分支处理；用七夕已验证链路回归，重做跨计划去重与日期边界测试。\n3. **并行核验费用依据：** 明确A/B/C及计算方法5，选真实供应商合同和ERP费用行，验证已扣费与跨期退货调整。\n4. **AI先输出审核草稿：** 能做投放/核销、会员、连带的有证据解释；缺人群任务、ROI成本或因果对照时明确缺失。AI不直接下发券或确认费用。')
    md('questions','## 仍需核验的接口与业务事实\n\n- CRM营销计划表当前只有607租户记录，不能拿它当601投放任务来源；七夕发放记录rule_id为空，scene_code只描述入口。需要查明实际发券配置、任务及目标人群存储位置。\n- ERP/CRM创建草稿、审核、停发、幂等和回执接口未验收；读库成功不等于可自动发布。\n- GIADA等权益券的实际兑现记录、品牌承担协议、ERP费用原行仍待业务样本核对。\n- 核查末段补查商品行供应商和跨期销售退货时数据库读取失败，未把失败查询当成0。因此本轮没有完成跨期退货金额与供应商最终结算验算。')
    md('limits','## 使用限制\n\n这是一份只读数据准备度核查，不是全库审计、活动增量评估或正式结算报告。七夕券资产后续日志未检出，并不能证明没有只退商品、不退券的跨期交易。正在投放的海蓝之谜券尚未到有效期结束，不据当前使用量判断成败。\n\nPAPI的GPP中文返回存在编码显示问题；本次数字、日期和ID核对与本地中文名称分开，未改源数据。没有配置同步任务、发布活动、发券、写ERP费用或向外部模型发送会员身份明细。')
    sample_rows=[]
    for r in rows('bi_selected_templates'):
        if r['id'] in ('529693','532669','532644'):
            sample_rows.append({'id':r['id'],'name':r['name'],'type':r['type'],'erp_type':r['third_party_no'] or '无','period':r['issue_start'][:10]+' 至 '+r['issue_end'][:10],'money':str(r['money']) if r['money'] is not None else '未提供'})
    now=datetime.now().astimezone().isoformat()
    artifact={'surface':'report','manifest':{'version':1,'surface':'report','title':'Coupon Data Readiness','description':'活动与卡券营销的数据关联核查｜2026年9月5日','generatedAt':now,'sources':sources,'blocks':blocks,'charts':[{'id':'preissue_chart','title':'七夕四券预发占比','subtitle':'各券中在8月14日前发放的资产占比；不是使用率。','type':'bar','dataset':'preissue','sourceId':'pg_qixi_events','encodings':{'x':{'field':'coupon','type':'nominal','label':'券种'},'y':{'field':'early_rate','type':'quantitative','format':'percent','label':'预发资产占比'}},'valueFormat':'percent','layout':'full'}],'tables':[{'id':'samples_table','title':'投放样本与兑现路径','dataset':'samples','sourceId':'bi_selected_templates','layout':'full','defaultSort':{'field':'id','direction':'asc'},'columns':[{'field':'name','label':'模板名称'},{'field':'id','label':'模板ID'},{'field':'type','label':'源类型'},{'field':'erp_type','label':'ERP券种'},{'field':'period','label':'投放期'},{'field':'money','label':'金额字段原值'}]}]},'snapshot':{'version':1,'generatedAt':now,'status':'ready','datasets':{'preissue':chart_rows,'samples':sample_rows}},'sources':sources}
    (BASE/'artifact.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2))
    # Audit notebook preserves the actual executed SQL and aggregate results, no credentials.
    cells=[{'cell_type':'markdown','metadata':{},'source':['# 卡券数据核查证据\n','只读快照；包含成功查询、失败查询和跨源集合比对。原始身份/券号不落盘。\n','复跑单条：导入 reports.coupon_data_audit_20260905.run(label, source, sql)。']}]
    for path in sorted(BASE.glob('*.json')):
        if path.name=='artifact.json': continue
        e=json.loads(path.read_text())
        if 'label' not in e: continue
        cells.append({'cell_type':'markdown','metadata':{},'source':[f"## {e['label']}\n",f"来源：{e.get('source','CRM/PG集合比对')}；查询时间：{e.get('started_at',e.get('checked_at',''))}\n"]})
        cells.append({'cell_type':'code','metadata':{},'execution_count':None,'source':['# 已执行查询/集合比对证据；本单元仅展示保存的结果。\n','evidence = '+repr(e)+'\n','evidence\n'],'outputs':[{'output_type':'display_data','metadata':{},'data':{'application/json':e,'text/plain':[json.dumps(e,ensure_ascii=False,indent=2)]}}]})
    notebook={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}},'nbformat':4,'nbformat_minor':5}
    (BASE/'evidence.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=2))
    qa={'oracle_pg_groups_equal':True,'asset_sets_equal':True,'history_population_reconciled':True,'sources':len(sources),'report_blocks':len(blocks),'chart_contract':'4 categories; preissue share at coupon asset grain; zero baseline; no causal/efficiency ranking; native full-width bar, single measure, no redundant legend; exact sample template lookup table.','audience':'product stakeholders','scope':'data readiness, not actual settled fees','evidence_window':'2026-09-05 12:50–12:56 Asia/Shanghai; later connection failures excluded from results','report_structure':'Title, Executive Summary, findings, next steps, further questions, caveats; sources kept in metadata.'}
    (BASE/'validation.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    print(json.dumps(qa,ensure_ascii=False))


if __name__=='__main__':
    build()
