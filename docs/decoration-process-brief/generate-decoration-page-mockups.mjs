import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const outDir = new URL("./page-mockups/", import.meta.url).pathname;
mkdirSync(outDir, { recursive: true });

const css = `
  <style>
    svg { background: #eef2f7; }
    text { font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif; fill: #182033; }
    .app { fill: #f4f7fb; }
    .top { fill: #111827; }
    .side { fill: #ffffff; stroke: #dbe2ee; }
    .main { fill: #f6f8fb; }
    .panel { fill: #ffffff; stroke: #d9e1ef; stroke-width: 1; rx: 10; }
    .soft { fill: #f8fafc; stroke: #e2e8f0; rx: 8; }
    .blue { fill: #e8f1ff; stroke: #79a8f7; rx: 8; }
    .green { fill: #e8f7ef; stroke: #64bd84; rx: 8; }
    .amber { fill: #fff5df; stroke: #e4b551; rx: 8; }
    .red { fill: #fff0ef; stroke: #e27468; rx: 8; }
    .purple { fill: #f1edff; stroke: #9279e6; rx: 8; }
    .muted { fill: #687386; }
    .white { fill: #ffffff; }
    .title { font-size: 28px; font-weight: 800; }
    .h2 { font-size: 20px; font-weight: 800; }
    .h3 { font-size: 17px; font-weight: 800; }
    .body { font-size: 15px; fill: #364154; }
    .small { font-size: 13px; fill: #647084; }
    .tiny { font-size: 12px; fill: #7b8495; }
    .nav { font-size: 15px; fill: #334155; }
    .nav-on { font-size: 15px; font-weight: 800; fill: #1d4ed8; }
    .btn { fill: #2563eb; rx: 7; }
    .btn2 { fill: #ffffff; stroke: #cfd8e8; rx: 7; }
    .btnText { font-size: 14px; font-weight: 700; fill: #ffffff; }
    .btnText2 { font-size: 14px; font-weight: 700; fill: #334155; }
    .tag { rx: 13; }
    .tagText { font-size: 12px; font-weight: 700; }
    .line { stroke: #d8dfeb; stroke-width: 1; }
    .th { font-size: 13px; font-weight: 800; fill: #475569; }
    .td { font-size: 13px; fill: #334155; }
  </style>`;

function base(title, subtitle) {
  return `
    <rect class="app" x="0" y="0" width="1600" height="1000"/>
    <rect class="top" x="0" y="0" width="1600" height="64"/>
    <text class="white" x="32" y="40" font-size="22" font-weight="800">ShopView</text>
    <text class="white" x="1350" y="39" font-size="14">装修流程迁移原型</text>
    <rect class="side" x="0" y="64" width="230" height="936"/>
    <text class="nav" x="32" y="118">合同台账</text>
    <rect x="20" y="145" width="190" height="42" fill="#e8f1ff" rx="8"/>
    <text class="nav-on" x="32" y="172">装修管理</text>
    <text class="nav" x="32" y="224">夜间施工</text>
    <text class="nav" x="32" y="270">费用退款</text>
    <text class="nav" x="32" y="316">开柜流转</text>
    <text class="nav" x="32" y="362">ERP 修改记录</text>
    <rect class="main" x="230" y="64" width="1370" height="936"/>
    <text class="title" x="270" y="120">${title}</text>
    <text class="small" x="270" y="148">${subtitle}</text>
  `;
}

function button(x, y, text, primary = true, w = 94) {
  return `<rect class="${primary ? "btn" : "btn2"}" x="${x}" y="${y}" width="${w}" height="34"/><text class="${primary ? "btnText" : "btnText2"}" text-anchor="middle" x="${x + w / 2}" y="${y + 22}">${text}</text>`;
}

function panel(x, y, w, h, title) {
  return `<rect class="panel" x="${x}" y="${y}" width="${w}" height="${h}"/><text class="h2" x="${x + 22}" y="${y + 36}">${title}</text>`;
}

function field(x, y, label, value, w = 230) {
  return `
    <text class="tiny" x="${x}" y="${y}">${label}</text>
    <rect class="soft" x="${x}" y="${y + 10}" width="${w}" height="38"/>
    <text class="body" x="${x + 12}" y="${y + 35}">${value}</text>
  `;
}

function tag(x, y, text, kind = "blue", w = 78) {
  const textColor = kind === "amber" ? "#8a5a10" : kind === "green" ? "#166534" : kind === "red" ? "#991b1b" : "#1d4ed8";
  return `<rect class="${kind} tag" x="${x}" y="${y}" width="${w}" height="26"/><text class="tagText" fill="${textColor}" text-anchor="middle" x="${x + w / 2}" y="${y + 18}">${text}</text>`;
}

function table(x, y, widths, headers, rows) {
  let out = `<rect class="soft" x="${x}" y="${y}" width="${widths.reduce((a, b) => a + b, 0)}" height="${40 + rows.length * 42}"/>`;
  let cx = x;
  headers.forEach((h, i) => {
    out += `<text class="th" x="${cx + 14}" y="${y + 26}">${h}</text>`;
    if (i > 0) out += `<line class="line" x1="${cx}" y1="${y}" x2="${cx}" y2="${y + 40 + rows.length * 42}"/>`;
    cx += widths[i];
  });
  out += `<line class="line" x1="${x}" y1="${y + 40}" x2="${x + widths.reduce((a, b) => a + b, 0)}" y2="${y + 40}"/>`;
  rows.forEach((row, r) => {
    cx = x;
    row.forEach((cell, i) => {
      out += `<text class="td" x="${cx + 14}" y="${y + 67 + r * 42}">${cell}</text>`;
      cx += widths[i];
    });
    if (r < rows.length - 1) out += `<line class="line" x1="${x}" y1="${y + 82 + r * 42}" x2="${x + widths.reduce((a, b) => a + b, 0)}" y2="${y + 82 + r * 42}"/>`;
  });
  return out;
}

function progress(x, y, steps, active) {
  const gap = 145;
  let out = "";
  steps.forEach((s, i) => {
    const cx = x + i * gap;
    if (i > 0) out += `<line x1="${cx - gap + 26}" y1="${y}" x2="${cx - 26}" y2="${y}" stroke="${i <= active ? "#2563eb" : "#cbd5e1"}" stroke-width="3"/>`;
    out += `<circle cx="${cx}" cy="${y}" r="18" fill="${i <= active ? "#2563eb" : "#e2e8f0"}"/><text fill="${i <= active ? "#fff" : "#64748b"}" text-anchor="middle" x="${cx}" y="${y + 6}" font-size="14" font-weight="800">${i + 1}</text>`;
    out += `<text class="tiny" text-anchor="middle" x="${cx}" y="${y + 42}">${s}</text>`;
  });
  return out;
}

const overview = `
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
${css}
${base("装修项目详情", "一张装修单贯穿交保证金、夜间施工、验收退款、开柜流转")}
${button(1410, 100, "发起报备", true, 96)}${button(1288, 100, "上传附件", false, 96)}
${panel(270, 180, 940, 170, "项目主信息")}
${tag(1110, 202, "施工中", "green", 82)}
${field(292, 238, "品牌/柜组", "爱慕 / 中心三部", 210)}
${field(532, 238, "铺位", "6F 厅房", 160)}
${field(722, 238, "施工单位", "某某装饰工程有限公司", 250)}
${field(1002, 238, "现场负责人", "张工 138****9356", 180)}
${field(292, 305, "预计施工周期", "2026-06-08 至 2026-06-20", 250)}
${field(562, 305, "人数", "7 人", 110)}
${field(702, 305, "来源", "合同完成后发起", 190)}
${field(922, 305, "当前节点", "夜间施工报备", 190)}
${panel(1235, 180, 305, 170, "关键提醒")}
${tag(1260, 230, "待上传", "amber", 76)}<text class="body" x="1348" y="249">纸质签到表</text>
${tag(1260, 275, "未完成", "red", 76)}<text class="body" x="1348" y="294">退保证金</text>
${tag(1260, 320, "未生成", "blue", 76)}<text class="body" x="1348" y="339">开柜流转单</text>
${panel(270, 380, 1260, 130, "流程进度")}
${progress(335, 440, ["合同完成", "交保证金", "施工证", "夜间报备", "进出场", "验收", "退款", "开柜流转"], 3)}
${panel(270, 540, 610, 310, "费用明细")}
${table(292, 595, [150, 120, 110, 120, 140], ["费用项", "金额", "是否可退", "状态", "退款账号"], [["施工证工本费", "200.00", "否", "已缴", "-"], ["施工保证金", "5000.00", "是", "已缴", "已填写"], ["施工押金", "3000.00", "是", "已缴", "已填写"], ["围挡费用", "800.00", "视规则", "待确认", "-"]])}
${panel(910, 540, 620, 310, "最近动态")}
<text class="body" x="935" y="610">06-02 09:20  业务上传施工材料和图纸</text>
<line class="line" x1="935" y1="630" x2="1495" y2="630"/>
<text class="body" x="935" y="665">06-02 10:35  工程审核通过，生成应缴费用</text>
<line class="line" x1="935" y1="685" x2="1495" y2="685"/>
<text class="body" x="935" y="720">06-02 14:10  施工方完成扫码缴费</text>
<line class="line" x1="935" y1="740" x2="1495" y2="740"/>
<text class="body" x="935" y="775">06-02 15:00  物业发放施工证</text>
<line class="line" x1="935" y1="795" x2="1495" y2="795"/>
<text class="body" x="935" y="830">06-02 16:30  业务发起夜间施工报备</text>
</svg>`;

const deposit = `
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
${css}
${base("交保证金申请", "迁移 OA 原交保证金流程：图纸材料、施工单位、费用明细、缴费凭证")}
${button(1400, 100, "提交审批", true, 98)}${button(1280, 100, "保存草稿", false, 98)}
${panel(270, 180, 1260, 110, "基础信息")}
${field(292, 238, "合同编号", "HT-2026-0602-008", 210)}
${field(532, 238, "品牌/柜组", "Salomon / 中心二部", 230)}
${field(782, 238, "铺位", "1F-6F", 150)}
${field(962, 238, "发起部门", "品类部", 160)}
${field(1152, 238, "施工类型", "进场装修", 160)}
${panel(270, 320, 610, 255, "图纸与审核材料")}
<rect class="blue" x="292" y="375" width="250" height="70"/><text class="h3" x="315" y="407">装修全套图</text><text class="small" x="315" y="430">已上传 3 个文件</text>
<rect class="green" x="570" y="375" width="250" height="70"/><text class="h3" x="593" y="407">审批表</text><text class="small" x="593" y="430">工程已确认</text>
<rect class="soft" x="292" y="470" width="528" height="58"/><text class="body" x="315" y="505">审核意见：图纸完整，现场施工不得影响周边品牌营业。</text>
${panel(910, 320, 620, 255, "施工单位信息")}
${field(932, 378, "施工单位", "常州某某装饰工程有限公司", 300)}
${field(1260, 378, "负责人", "吴浩", 150)}
${field(932, 445, "联系方式", "158****0035", 180)}
${field(1145, 445, "开户行", "建设银行常州支行", 220)}
${field(932, 512, "银行账号", "6222 **** **** 9271", 300)}
${panel(270, 605, 1260, 285, "费用明细与缴费凭证")}
${table(292, 660, [190, 130, 130, 160, 180, 260], ["费用项", "应缴金额", "是否可退", "退款账号", "缴费状态", "凭证"], [["施工证工本费", "200.00", "否", "不需要", "待扫码缴费", "未上传"], ["施工证保证金", "1000.00", "是", "必填", "待扫码缴费", "未上传"], ["施工保证金", "5000.00", "是", "必填", "待扫码缴费", "未上传"], ["围挡及其他费用", "800.00", "按规则", "视规则", "待确认", "未上传"]])}
</svg>`;

const night = `
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
${css}
${base("夜间施工报备", "业务填报后自动进入物业汇总，安保按当日汇总表核验进出场")}
${button(1400, 100, "提交报备", true, 98)}${button(1270, 100, "生成汇总表", false, 112)}
${panel(270, 180, 820, 250, "报备信息")}
${field(292, 238, "施工日期", "2026-06-08", 160)}
${field(482, 238, "品牌/铺位", "爱慕 / 6F 厅房", 220)}
${field(732, 238, "施工方名称", "某某装饰工程有限公司", 260)}
${field(292, 305, "现场负责人", "陈伟", 140)}
${field(462, 305, "联系方式", "180****5718", 180)}
${field(682, 305, "人数", "7 人", 110)}
${field(292, 372, "施工事项", "6F 厅房装修", 220)}
${field(542, 372, "施工周期", "6.08 - 6.20", 180)}
${field(762, 372, "影响区域/措施", "周边区域 / 遮盖", 220)}
${panel(1120, 180, 410, 250, "安保控制")}
${tag(1145, 240, "准入规则", "blue", 86)}<text class="body" x="1248" y="259">必须在当日汇总表内</text>
${tag(1145, 295, "现场依据", "amber", 86)}<text class="body" x="1248" y="314">施工证 + 纸质签到</text>
${tag(1145, 350, "归档要求", "green", 86)}<text class="body" x="1248" y="369">签到表上传系统</text>
${panel(270, 460, 1260, 360, "当日夜间施工人员汇总表")}
${table(292, 515, [70, 150, 150, 120, 160, 190, 80, 140, 140, 170], ["序号", "部门/品牌", "装修地点", "负责人", "联系方式", "装修事项", "人数", "影响区域", "采取措施", "安保结果"], [["1", "中心七部", "6F 厅房", "陈伟", "180****5718", "6F 厅房装修", "7", "周边", "遮盖", "待核验"], ["2", "企划部", "1F-6F", "朱美亚", "138****0356", "物料安装", "5", "无", "无", "待核验"], ["3", "物业工程", "BF-6F", "吴浩", "158****0035", "绿植养护", "1", "无", "无", "待核验"], ["4", "品类一部", "兰蔻", "顾婷", "158****4556", "更换陈列", "2", "无", "无", "待核验"]])}
<rect class="amber" x="292" y="845" width="1210" height="42"/><text class="body" x="315" y="872">提示：物业确认汇总后同步安保；未报备人员默认不允许夜间进场。</text>
</svg>`;

const refund = `
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
${css}
${base("退保证金与开柜流转", "退保证金完成后自动生成开柜流转单，继续完成实测面积、用电功率和 ERP 条款更新")}
${button(1408, 100, "提交退款", true, 98)}${button(1282, 100, "保存测算", false, 98)}
${panel(270, 180, 1260, 130, "关联原交保证金流程")}
${field(292, 238, "原流程编号", "ZXSQ-2026-0602-015", 230)}
${field(532, 238, "品牌/柜位", "爱慕 / 6F 厅房", 210)}
${field(762, 238, "原缴费合计", "9,000.00", 160)}
${field(952, 238, "可退金额", "8,000.00", 160)}
${field(1142, 238, "退款账号", "张三 / 建设银行 / 6222****", 280)}
${panel(270, 340, 610, 300, "验收与扣款")}
<rect class="green" x="292" y="395" width="250" height="64"/><text class="h3" x="315" y="424">纸质验收单</text><text class="small" x="315" y="446">已上传，物业确认</text>
<rect class="blue" x="570" y="395" width="250" height="64"/><text class="h3" x="593" y="424">纸质签到表</text><text class="small" x="593" y="446">已上传 2 页</text>
${table(292, 490, [180, 130, 260], ["扣款项", "金额", "依据"], [["管理费扣款", "300.00", "按施工天数计算"], ["水电费扣款", "180.00", "现场核算"], ["施工罚款", "0.00", "无违规记录"]])}
${panel(910, 340, 620, 300, "退款结果")}
${field(932, 398, "原收保证金", "8,000.00", 170)}
${field(1140, 398, "扣款合计", "480.00", 150)}
${field(1320, 398, "应退金额", "7,520.00", 150)}
<rect class="red" x="932" y="485" width="510" height="70"/><text class="h3" x="955" y="515">财务付款确认</text><text class="small" x="955" y="538">付款完成后回填退款凭证，流程进入开柜流转。</text>
${panel(270, 670, 1260, 210, "开柜流转单")}
${field(292, 728, "实测面积", "86.50 平方米", 180)}
${field(512, 728, "照明功率", "12.5 kW", 150)}
${field(702, 728, "其他功率", "3.2 kW", 150)}
${field(892, 728, "电费条款", "按实测功率调整", 210)}
${field(1132, 728, "租金条款", "按实测面积调整", 210)}
${field(292, 795, "ERP 修改状态", "待传 ERP", 180)}
${field(512, 795, "ERP 单号/截图", "待回填", 180)}
${field(732, 795, "下一处理人", "合同/财务经办", 200)}
</svg>`;

const files = [
  ["01-project-detail-overview.svg", overview],
  ["02-deposit-application.svg", deposit],
  ["03-night-construction-page.svg", night],
  ["04-refund-opening-page.svg", refund],
];

for (const [name, svg] of files) {
  writeFileSync(join(outDir, name), svg.trim() + "\n", "utf8");
}

writeFileSync(
  join(outDir, "README.md"),
  [
    "# 装修流程页面原型图",
    "",
    "- `01-project-detail-overview.svg`：装修项目详情总览",
    "- `02-deposit-application.svg`：交保证金申请",
    "- `03-night-construction-page.svg`：夜间施工报备",
    "- `04-refund-opening-page.svg`：退保证金与开柜流转",
    "",
  ].join("\n"),
  "utf8",
);

console.log(files.map(([name]) => join(outDir, name)).join("\n"));
