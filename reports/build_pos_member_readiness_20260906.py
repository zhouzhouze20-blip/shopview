"""Build source-backed report artifacts from saved, read-only aggregate queries."""
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal

BASE = Path(__file__).resolve().parent / 'pos-member-readiness-20260906'

def evidence(label):
    return json.loads((BASE / f'{label}.json').read_text())

def rows(label):
    e = evidence(label)
    assert 'error' not in e, label
    return e['rows']

def build():
    coupons = []
    for r in rows('bi_qixi_link'):
        coupons.append({'template_id':r['template_id'], 'name':r['name'], 'coupon_type':r['third_party_no'], 'issued':int(r['coupons']), 'consume_flows':int(r['consume_flows']), 'return_flows':int(r['return_flows']), 'store':'601', 'valid_start':'2026-08-14', 'valid_end':'2026-08-19'})
    assert sum(r['issued'] for r in coupons) == 1925
    assert sum(r['consume_flows'] for r in coupons) == 711
    assert sum(r['return_flows'] for r in coupons) == 63
    coupons.sort(key=lambda r:r['issued'], reverse=True)
    histories=[]
    for store in ['601','603']:
        h={k:int(v) for k,v in rows(f'shared_history_{store}_dated')[0].items()}
        ho={k:int(v) for k,v in rows(f'shared_history_{store}_open')[0].items()}
        clear=h['one_row']+h['repeated_same_level']
        assert clear+h['conflicting_levels']+h['no_history'] == h['members']
        assert clear == ho['one_row']+ho['repeated_same_level']
        assert h['no_history']==h['new_without_history']+h['existing_without_history']
        histories.append({'store':store, 'members':h['members'], 'consistent':clear, 'conflicting':h['conflicting_levels'], 'new_after_start':h['new_without_history'], 'existing_unknown':h['existing_without_history'], 'consistent_rate':clear/h['members'], 'cutoff':'2026-08-14 00:00:00 Asia/Shanghai', 'history_tenants':'601,603'})
    pg={r['tcflzy']:(int(r['n']),Decimal(r['amount'])) for r in rows('flow_counts_603_pg_fixed')}
    crm={r['tcflzy']:(int(r['n']),Decimal(r['amount'])) for r in rows('flow_counts_603_crm_day_normalized')}
    assert pg == crm
    assert evidence('return_asset_603_triangulation')['record']['rows'][0]['template_id']=='527239'
    assert Decimal(rows('pg_qixi_late_returns_fixed')[0]['return_sales']) == Decimal('-3626')
    titles={
        'bi_qixi_link':'601四券模板、资产及动作流水',
        'pilot_assets_601':'601发放资产唯一性与人数',
        'pilot_assets_603':'603发放资产唯一性与人数',
        'bi_603_link':'603两张福利券关联流水',
        'member_identity_601':'601会员身份桥接',
        'member_identity_603':'603会员身份桥接',
        'shared_history_601_dated':'601共享等级历史覆盖',
        'shared_history_603_dated':'603共享等级历史覆盖',
        'shared_history_601_open':'601空结束时间敏感性核查',
        'shared_history_603_open':'603空结束时间敏感性核查',
        'shared_level_dictionary':'两店等级代码与名称核对',
        'history_dates_601':'601等级历史前置基线',
        'history_dates_603':'603等级历史前置基线',
        'pg_qixi_ticket_link':'601消费券流水与小票身份',
        'pg_603_ticket_link':'603日期券种范围的小票关联',
        'pg_qixi_supplier_lines_fixed':'601消费小票商品及供应商',
        'pg_qixi_late_returns_fixed':'601原消费小票的跨期商品退货',
        'late_returns_document_types':'跨期退货单据类型与金额',
        'flow_counts_603_pg_fixed':'603日期券种范围的项目ODS日志',
        'flow_counts_603_crm_day_normalized':'603日期归一化后的CRM日志',
        '603_return_template':'603福利券与其他品类券模板',
        'gpp_activity_periods':'GPP源库活动档期2204与2205',
        'pg_pop_aug':'项目库ERP档期名称及日期',
        'crm603_pos_templates':'603不同阶段POS模板',
    }
    sources=[]
    for label,title in titles.items():
        e=evidence(label)
        assert 'error' not in e
        sources.append({'id':label,'label':title,'query':{'engine':{4:'PostgreSQL',14:'MySQL',7:'Oracle'}[e['source_id']]+' via PAPI','language':'SQL','sql':e['sql'],'executed_at':e['finished_at'],'description':title+'；查询中的来源表、过滤范围及聚合粒度为准。'}})
    sources.extend([
        {'id':'business_confirmation','label':'用户本轮确认两店共用会员等级','query':{'description':'2026-09-06用户明确确认601和603共用会员等级；不等同于指定601历史为权威或允许跨店销售权限互通。'}},
        {'id':'return_triangulation','label':'603单笔退券跨源追溯','query':{'description':'以项目库唯一P资产在CRM发放记录、CRM券日志和GPP源日志中追查。该资产属于模板527239，三方均可见P一次50元；不是532632/532633福利券的退券。原始券号仅内存传递，未写入报告。','executed_at':evidence('return_asset_603_triangulation')['finished_at']}}
    ])
    blocks=[]
    def md(id,body,source=None):
        b={'id':id,'type':'markdown','body':body}
        if source:b['sourceId']=source
        blocks.append(b)
    title='601与603活动数据准备度核查'
    md('title','# '+title)
    md('summary','## Executive Summary\n\n**建议进入“POS与共享会员数据底座＋活动归属”首期建设，先交付经营分析，不直接启用正式费用结算或ERP/CRM自动发布。**\n\n- 601四券1,925张、603两张福利券40,935张，可关联CRM会员身份与券流水，适合作为首版回归样本。\n- 用户确认两店共用等级后，跨租户复核消除了大部分表面缺失：601有781人、603有10,013人等级一致可用；分别3人、305人历史等级冲突需单列。\n- 活动归属必须落实到模板和资产；同时跟踪跨期商品退货。否则会把别的品类券计入活动，或过早封账。')
    md('scope','## 范围与取数时间\n\n2026-09-06上午北京时间通过PAPI只读核查：601七夕四券532623—532626；603的50元/100元福利券532632、532633，均以8月14—19日使用期为试点。发放期独立核算，不截断活动前预发。\n\n本报告是数据与实施准备度判断，不是全门店全券审计或完整经营效果报告。各源不是同一事务快照，生成时间不代表源系统同步时间；没有新增POS/会员ETL、修改业务数据或发券。')
    md('coupons','## POS模板、券资产和流水能接上\n\n601四券共1,925张，关联711笔消费O、63笔退券P；603两张福利券共40,935张，关联196笔消费O、0笔退券P。两店试点分别涉及828和10,331名获券会员，均能通过正确身份链匹配member_scenes。\n\n**会员桥接固定为：发放记录mem_id → member.id → member.member_scenes_id → member_scenes.id。** 不能把两个表的主键直接等同。图中是资产发放量，不是核销率或活动效率。','bi_qixi_link')
    blocks.append({'id':'coupon_chart_block','type':'chart','chartId':'coupon_chart'})
    blocks.append({'id':'coupon_table_block','type':'table','tableId':'coupon_table'})
    md('shared','## 会员等级按共享身份还原，不按消费门店切断\n\n两店VIP1—VIP4代码和名称一致，且用户确认共用等级。本次以共享member_scenes身份，合并601/603的等级历史，在8月14日00:00匹配有效区间。\n\n同一时点只有一个等级代码才计入“一致可用”；同级重复可在分析层去重，但原始行必须保留。多等级冲突单列，不默认取最高、最新或601优先。共享等级也不意味着跨店销售明细可以突破现有权限。','shared_level_dictionary')
    blocks.append({'id':'history_table_block','type':'table','tableId':'history_table'})
    md('history_caveat','### 覆盖率与剩余问题\n\n601：781人等级一致、3人冲突、44人活动后注册；没有此前注册且完全缺历史的会员。603：10,013人等级一致、305人冲突、8人活动后注册、5名此前注册者缺历史。\n\n空结束时间按“不匹配”或“持续有效”测试，以上一致/冲突/缺失人数不变，但重复行数变化。正式规则仍须核验边界、状态字段与权威事件来源。这里的冲突是当前候选区间算法发现的等级差异，不是认定CRM业务错误。\n\n先前只筛603租户所得9,399名无区间不是最终缺失数；上述共享口径取代该初步结论。','shared_history_603_dated')
    md('baseline','## 八月后的业务数据仍需要八月前的会员基线\n\n601试点等级历史有2,190行起始于8月1日前；603本店历史也有6,809行起始于8月1日前。若把等级历史机械限制为8月后创建，会丢失活动时仍有效的等级。\n\n建议POS事实继续按“8月1日起新增、更新或使用”采集并补齐关联模板；会员仅同步这些业务涉及的身份及其必要的历史基线。优先补覆盖8月1日的有效区间和后续变化；无法证明基线完整时，按涉及会员取完整轨迹，而不是全库会员全历史。此例外应作为采集范围明确确认。','history_dates_601')
    md('ownership','## 日期与券种相同，不等于属于同一活动\n\n603按Q券种和8月14—19日有效期查询时，会多出1笔P退券。逐资产追查证实，它属于“品类券”模板527239，不属于本次福利券532632/532633；GPP源库与CRM均有这一笔50元退券。\n\n因此活动归属必须保存“计划/阶段 → 模板 → 资产”，日期、券种仅为核验条件。原日志活动编号为空时，不自动改写源数据。','return_triangulation')
    md('date_types','### 跨源日期先统一业务日口径\n\nCRM有效期结束含23:59:59，项目券日志按日期存储。用结束时间等于当天00:00的条件会误查为0；按业务日范围归一后，两边M/O/P三组笔数与带符号金额一致。该范围含上面的其他品类券，不能把它直接当福利券模板口径。','flow_counts_603_crm_day_normalized')
    md('phases','## ERP档期与营销阶段不应强制一一对应\n\nERP2204覆盖8月14日至9月1日，名称包含夏日活动及开学季两个阶段；603可见8月14—19日、8月20—9月1日两批不同ID的50元/100元福利券。2205则是601七夕8月14—19日。\n\n设计上保留“总计划—活动/阶段—投放批次”，阶段可绑定同一ERP档期下不同规则和CRM模板。603模板与2204的正式业务归属仍需规则核准，不能仅凭名称日期自动入档。','gpp_activity_periods')
    md('basket','## 连带分析有商品与供应商基础，但不能按券流水重复加销售\n\n601的711笔消费券流水唯一匹配小票；去重后关联到671张有商品明细的小票、805行商品，涉及80个品牌、70个供应商，供应商标识缺失为0。\n\n这些是整张消费小票的商品，不等于全部满足券适用规则或全部由供应商承担费用。先按小票去重算连带，再按支付/优惠/商品适用范围分配。持券人与小票会员不同的248笔消费流水单独解释；另有11笔小票无会员。不得把关联消费直接称为增量销售。','pg_qixi_supplier_lines_fixed')
    md('returns','## 活动结束后仍有商品退货\n\n通过原单号回链，601试点在8月21—24日有3张退货单、4行商品，带符号商品销售收入合计−3,626元，单据类型4。查询观察范围截至9月6日当前可见数据。\n\n该金额不是退券金额、商场损失或供应商应扣金额。应分别保存商品退货、券回退和费用冲销关系；活动结束后进入观察期，已结算部分走后续调整单，不能覆盖已确认结算版本。','pg_qixi_late_returns_fixed')
    md('delivery','## 首期交付顺序与验收门槛\n\n1. **补数据底座。** POS模板和发放资产与现有gift采集分开管理；会员身份共享、源租户保留、等级基线留存。复用现有ERP券日志和小票，显示源更新时间、加载时间、失败和待核数量。\n2. **先做统一活动工作台。** 年度新人计划、专项活动、阶段品牌计划共用主档；支持阶段、模板及规则版本。POS兑现和礼品/权益兑现分支统计。历史活动先导入绑定，不急于自动发布。\n3. **交付会员与连带分析。** 同时区分集团新客/本店首购、获券人/购买人、活动时等级/当前等级；冲突未知单列。对照601/603样本回归，同票多券不重计。\n4. **费用与AI分级上线。** 费用先试算、复核合同及ERP实际费用行，再确认供应商分摊与跨期调整。AI先做标准审核草稿，引用固定指标证据，不自行计算应扣金额。\n5. **最后验收ERP/CRM发布。** 验证草稿、审核、幂等、回执、失败重试、停发及版本映射后，才让活动从ShopView向外执行。')
    md('gates','## 当前可以做什么，哪些暂不能自动通过\n\n**可以推进：** POS资产与会员身份采集设计、共享等级冲突清单、活动模板绑定、去重小票连带、退货追踪、带质量提示的AI草稿。\n\n**需阻断自动确认：** 冲突会员的确定等级结论；未核准的603模板归属；没有适用商品及承担协议的供应商费用；未经接口验收的ERP/CRM活动发布。\n\n下一步最小实施包是POS/共享会员ODS与质量检查，不是一次性重做整个活动模块。本轮没有执行该采集或数据库迁移。')
    md('limitations','## 方法限制与后续核查\n\n- 全门店POS八月范围体量查询超时，不能宣称全量POS完整性验收完成；本轮结论限于六个试点模板。\n- 会员当前生命周期或最后消费时间不能代替活动前消费历史。首购、沉睡、复购仍需独立选择足够长的前后观察窗，并核对退货与匿名消费。\n- 等级冲突需要检查状态/规则执行事件、旧系统迁移及权威链路；不能用当前等级倒填。\n- 财务承担公式、实际费用行及自动发布接口本轮未验收。ERP源名称有编码显示问题，中文以项目镜像对照，未修改源内容。\n- 故障/错误查询保留在证据笔记本；报告使用修正后成功结果，不把超时或错误当成零。所有表及SQL均为聚合证据，无客户姓名、电话或原始券号。')
    now=datetime.now().astimezone().isoformat()
    artifact={'surface':'report','manifest':{'version':1,'surface':'report','title':title,'description':'共享会员口径、POS归属、跨期退货与首期实施边界','generatedAt':now,'sources':sources,'blocks':blocks,'charts':[{'id':'coupon_chart','title':'601七夕四券发放资产数','subtitle':'四类券发放规模不同，数量不能单独代表活动效率。','type':'bar','dataset':'coupons','sourceId':'bi_qixi_link','encodings':{'x':{'field':'name','type':'nominal','label':'券模板'},'y':{'field':'issued','type':'quantitative','label':'发放资产（张）'}},'layout':'full'}],'tables':[{'id':'coupon_table','title':'601四券模板与动作流水','dataset':'coupons','sourceId':'bi_qixi_link','layout':'full','defaultSort':{'field':'issued','direction':'desc'},'columns':[{'field':'name','label':'名称'},{'field':'template_id','label':'模板ID'},{'field':'coupon_type','label':'ERP券种'},{'field':'issued','label':'发放资产数'},{'field':'consume_flows','label':'消费流水笔数'},{'field':'return_flows','label':'退券流水笔数'}]},{'id':'history_table','title':'活动开始时共享等级覆盖','dataset':'histories','sourceId':'shared_history_603_dated','sourceIds':['shared_history_601_dated','shared_history_603_dated'],'layout':'full','defaultSort':{'field':'store','direction':'asc'},'columns':[{'field':'store','label':'获券门店'},{'field':'members','label':'获券会员'},{'field':'consistent','label':'等级一致可用'},{'field':'conflicting','label':'等级冲突'},{'field':'new_after_start','label':'活动后注册'},{'field':'existing_unknown','label':'既有会员缺历史'}]}]},'snapshot':{'version':1,'generatedAt':now,'status':'ready','datasets':{'coupons':coupons,'histories':histories}},'sources':sources}
    (BASE/'artifact.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2))
    cells=[{'cell_type':'markdown','metadata':{},'source':['# POS与共享会员核查证据\n只读查询结果快照；共享等级业务口径由用户于2026-09-06确认。代码单元展示已执行查询证据，不会自动连接生产库。\n单条复查：从reports导入pos_member_readiness_20260906.run(label, source_id, sql)。参数化资产追溯需先重跑selector_sql，内部绑定单个资产ID，不打印客户标识。']}]
    for p in sorted(BASE.glob('*.json')):
        e=json.loads(p.read_text())
        if 'label' not in e: continue
        cells.append({'cell_type':'code','metadata':{},'execution_count':None,'source':['evidence = '+repr(e)+'\nevidence\n'],'outputs':[{'output_type':'display_data','metadata':{},'data':{'application/json':e,'text/plain':[json.dumps(e,ensure_ascii=False,indent=2)]}}]})
    notebook={'cells':cells,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},'language_info':{'name':'python'}},'nbformat':4,'nbformat_minor':5}
    for i,c in enumerate(cells):c['id']=f'evidence-{i}'
    (BASE/'evidence.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=2))
    qa={'passed':True,'checks':['601资产/消费/退券求和','共享等级队列闭合','空结束时间敏感性','603跨源动作笔数及金额一致','603非目标模板退券定位','跨期退货带符号金额'],'chart_contract':{'question':'四种601试点券的发放规模如何分布','family':'bar','variant':'single series','rows':4,'grain':'template asset count','palette':'native theme single series; no redundant category color','baseline':'zero','surface':'native MCP full-width report','final_qa':'native artifact validation then render'},'history_rates':histories,'sources':len(sources),'limitations':['not a complete POS audit','shared level authority/status semantics unresolved','no formal settlement','no ERP/CRM writes']}
    (BASE/'validation.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    print(json.dumps(qa,ensure_ascii=False))

if __name__=='__main__':build()
