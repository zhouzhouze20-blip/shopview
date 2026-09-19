import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import XLSX from "xlsx-js-style";
import { buildCampaignWorkbook, filterCampaigns } from "./coupon-campaign.ts";
import { MODULE_PERMISSION_REQUIREMENTS } from "./module-permissions.ts";

test("export keeps identifiers as text and contains all audit sheets", () => {
  const r={scope:{name:"七夕",store_code:"601",start_date:"2026-08-14",end_date:"2026-08-19",coupon_types:["B","E","H","M"]},
    generated_at:"2026-08-31",definitions:["退货按原小票"],quality:{unmatched_use_flows:0},coupons:[],member_levels:[],brands:[],
    sales_lift:{status:"estimated",method:"同星期+对照",baseline_weeks:4,day_count:6,activity_start_date:"2026-08-14",activity_end_date:"2026-08-19",baseline_periods:[{week_no:1,start_date:"2026-08-07",end_date:"2026-08-12"}],actual_sales:120,expected_sales:105,estimated_increment:15,estimated_growth_rate:14.29,caveats:[]},
    members:[{member_no:"0018112325518793058",net_linked_sales:29800,own_store_net_sales:29800}],
    tickets:[{member_match:"不一致",member_no:"0018112325518793058",billno:"13268560"}]};
  const wb=buildCampaignWorkbook(r);
  assert.deepEqual(wb.SheetNames,["报告口径","四券汇总","会员分层","会员明细","关联小票","会员不一致","连带品牌","ERP规则摘要","销售增长试算"]);
  assert.equal(wb.Sheets["会员明细"].A2.t,"s");
  assert.equal(wb.Sheets["会员明细"].A2.v,"0018112325518793058");
  assert.equal(wb.Sheets["会员不一致"].A2.v,"13268560");
  const liftRows=XLSX.utils.sheet_to_json(wb.Sheets["销售增长试算"],{header:1});
  assert.deepEqual(liftRows[3],["活动期日期","2026-08-14 至 2026-08-19"]);
  assert.deepEqual(liftRows[4],["历史同星期前1周","2026-08-07 至 2026-08-12"]);
});

test("campaign archive filters keep store name and period conditions independent",()=>{
  const campaigns=[
    {id:1,name:"中心七夕",store_code:"601",start_date:"2026-08-14",end_date:"2026-08-19"},
    {id:2,name:"中心国庆",store_code:"601",start_date:"2026-10-01",end_date:"2026-10-07"},
    {id:3,name:"新世纪七夕",store_code:"602",start_date:"2026-08-15",end_date:"2026-08-20"},
  ];
  assert.deepEqual(filterCampaigns(campaigns,{store_code:"601",name:"七夕",start_date:"2026-08-01",end_date:"2026-08-31"}).map(row=>row.id),[1]);
  assert.deepEqual(filterCampaigns(campaigns,{store_code:"",name:"",start_date:"2026-08-15",end_date:""}).map(row=>row.id),[2,3]);
});

test("campaign entry and report require dedicated permission",async()=>{
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["coupon-campaigns"],["activity_analysis.campaign.view"]);
  const page=await readFile(new URL("../pages/activity-analysis/campaigns.tsx",import.meta.url),"utf8");
  assert.match(page,/options.data\?\.can_manage/);
  assert.match(page,/exportCampaignWorkbook/);
  assert.match(page,/会员不一致仅为核查线索/);
  assert.match(page,/销售增长试算/);
  assert.match(page,/campaign-filter-store/);
  assert.match(page,/campaign-filter-name/);
  assert.match(page,/campaign-filter-start/);
  assert.match(page,/campaign-filter-end/);
  assert.match(page,/历史同星期基准日期/);
});

test("coupon flow operation labels agree with backend signed amount semantics",async()=>{
  const page=await readFile(new URL("../pages/activity-analysis/campaigns.tsx",import.meta.url),"utf8");
  assert.match(page,/O为核销、P为退券，U\/V分别为核销\/退券冲正/);
});

test("new audit sheets preserve asset IDs and separate post-period returns",()=>{
  const wb=buildCampaignWorkbook({scope:{name:'测试',store_code:'601',start_date:'2026-08-14',end_date:'2026-08-19',coupon_types:['H']},
    generated_at:'2026-09-06',definitions:[],quality:{},coupons:[],members:[],member_levels:[],brands:[],tickets:[],
    assets:[{coupon_type:'H',asset_id:'00000001234567890123',in_report:true}],coupon_flows:[],brand_details:[],
    ownership:{status_label:'候选范围，未人工确认',version:0,note:'',basis:'待业务确认'},
    post_activity_returns:{observed_through:'2026-09-06',return_sales:-100,caveat:'不改写活动期',details:[{billno:'0001',sales:-100}]},
  });
  assert.equal(wb.Sheets['券资产归属'].B2.t,'s');
  assert.equal(wb.Sheets['券资产归属'].B2.v,'00000001234567890123');
  assert.equal(wb.Sheets['活动后退货'].F2.v,-100);
  assert.ok(wb.SheetNames.includes('品牌供应商明细'));
  assert.ok(XLSX.utils.sheet_to_json(wb.Sheets['报告口径'],{header:1}).some(r=>r[0]==='归属状态' && r[1]==='候选范围，未人工确认'));
});
