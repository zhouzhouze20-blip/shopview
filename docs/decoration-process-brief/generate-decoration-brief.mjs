import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const outDir = new URL(".", import.meta.url).pathname;
mkdirSync(outDir, { recursive: true });

const css = `
  <style>
    svg { background: #f7f8fb; }
    text { font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif; fill: #172033; }
    .title { font-size: 42px; font-weight: 800; }
    .subtitle { font-size: 20px; fill: #5b6474; }
    .section-title { font-size: 24px; font-weight: 800; }
    .small { font-size: 16px; fill: #5b6474; }
    .label { font-size: 18px; font-weight: 700; }
    .body { font-size: 16px; fill: #354052; }
    .num { font-size: 18px; font-weight: 800; fill: #fff; }
    .lane { fill: #ffffff; stroke: #d8dde8; stroke-width: 1.4; }
    .card { fill: #ffffff; stroke: #cfd6e4; stroke-width: 1.5; rx: 16; }
    .blue { fill: #e7f0ff; stroke: #6a9cf5; }
    .green { fill: #e8f7ef; stroke: #55b97a; }
    .amber { fill: #fff4da; stroke: #e3ad3f; }
    .red { fill: #fff0ef; stroke: #e36a5c; }
    .purple { fill: #f0eaff; stroke: #8d73e6; }
    .dark { fill: #172033; }
    .line { stroke: #7b8495; stroke-width: 2.2; fill: none; marker-end: url(#arrow); }
    .dash { stroke: #9aa3b4; stroke-width: 2; stroke-dasharray: 7 7; fill: none; marker-end: url(#arrow); }
    .pill { rx: 18; }
    .note { fill: #fff; stroke: #e0e4ed; stroke-width: 1.2; rx: 14; }
  </style>`;

const defs = `
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#7b8495"/>
    </marker>
  </defs>`;

function lines(items, x, y, cls = "body", gap = 24) {
  return items.map((item, i) => `<text class="${cls}" x="${x}" y="${y + i * gap}">${item}</text>`).join("\n");
}

function card({ x, y, w, h, title, body = [], cls = "card", no, icon }) {
  const badge = no
    ? `<circle cx="${x + 30}" cy="${y + 31}" r="18" class="dark"/><text class="num" text-anchor="middle" x="${x + 30}" y="${y + 38}">${no}</text>`
    : "";
  const iconText = icon ? `<text font-size="28" x="${x + 22}" y="${y + 40}">${icon}</text>` : "";
  const titleX = x + (no ? 58 : icon ? 58 : 22);
  return `
    <rect class="${cls}" x="${x}" y="${y}" width="${w}" height="${h}"/>
    ${badge}${iconText}
    <text class="label" x="${titleX}" y="${y + 38}">${title}</text>
    ${lines(body, x + 24, y + 70)}
  `;
}

function header(title, subtitle) {
  return `
    <rect x="0" y="0" width="1600" height="120" fill="#ffffff"/>
    <text class="title" x="70" y="68">${title}</text>
    <text class="subtitle" x="72" y="100">${subtitle}</text>
  `;
}

const bg = `<rect x="0" y="0" width="1600" height="900" fill="#f7f8fb"/>`;

const overview = `
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
${defs}${css}
${bg}
${header("装修进撤场全流程总览", "将 OA 交保证金、退保证金、开柜流转单迁移到 ShopView 后的一条闭环链路")}
${card({ x: 70, y: 170, w: 230, h: 130, title: "合同完成", body: ["合同结果确认", "关联品牌、柜组、柜位"], cls: "card blue", no: 1 })}
${card({ x: 350, y: 170, w: 250, h: 130, title: "进场缴费", body: ["图纸和材料审核", "工本费、保证金缴纳"], cls: "card amber", no: 2 })}
${card({ x: 650, y: 170, w: 250, h: 130, title: "施工证领取", body: ["凭缴费凭证到物业", "确认进场条件"], cls: "card green", no: 3 })}
${card({ x: 950, y: 170, w: 250, h: 130, title: "夜间施工报备", body: ["业务邮件/系统报备", "物业汇总人员表"], cls: "card purple", no: 4 })}
${card({ x: 1250, y: 170, w: 250, h: 130, title: "安保进出场", body: ["按汇总表核验", "纸质签到进场/离场"], cls: "card", no: 5 })}
<path class="line" d="M300 235 H345"/><path class="line" d="M600 235 H645"/><path class="line" d="M900 235 H945"/><path class="line" d="M1200 235 H1245"/>
${card({ x: 210, y: 420, w: 270, h: 140, title: "现场验收", body: ["施工完成后现场确认", "纸质验收单签字归档"], cls: "card green", no: 6 })}
${card({ x: 560, y: 420, w: 280, h: 140, title: "退保证金流程", body: ["关联原缴费流程", "上传验收单和扣款依据"], cls: "card red", no: 7 })}
${card({ x: 920, y: 420, w: 280, h: 140, title: "扣款/退款", body: ["按实际情况扣款", "剩余金额退还账号"], cls: "card amber", no: 8 })}
${card({ x: 1280, y: 420, w: 260, h: 140, title: "开柜流转", body: ["实测面积、用电功率", "生成开柜流转单"], cls: "card blue", no: 9 })}
<path class="line" d="M1370 300 C1370 360 345 360 345 415"/>
<path class="line" d="M480 490 H555"/><path class="line" d="M840 490 H915"/><path class="line" d="M1200 490 H1275"/>
<rect class="note" x="190" y="650" width="1220" height="150"/>
<text class="section-title" x="230" y="695">汇报重点</text>
${lines(["1. 不是对接 OA，而是把交保证金、退保证金、开柜流转单迁移到 ShopView。", "2. 工本费、施工证保证金、施工押金/保证金必须分费用项管理，退款账号只对可退项目必填。", "3. 夜间施工汇总表、纸质签到表、纸质验收单短期保留，但必须电子归档。"], 230, 730, "body", 28)}
</svg>`;

const entry = `
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
${defs}${css}
${bg}
${header("进场缴费与施工证领取流程", "迁移 OA 原流程：百货营运-22 品牌进(撤)场施工保证金及费用缴纳流程")}
<rect class="lane" x="70" y="160" width="1480" height="120"/><text class="section-title" x="90" y="205">业务/前台</text>
<rect class="lane" x="70" y="300" width="1480" height="120"/><text class="section-title" x="90" y="345">工程/营运</text>
<rect class="lane" x="70" y="440" width="1480" height="120"/><text class="section-title" x="90" y="485">施工方/收款</text>
<rect class="lane" x="70" y="580" width="1480" height="120"/><text class="section-title" x="90" y="625">物业</text>
${card({ x: 250, y: 180, w: 250, h: 80, title: "发起进场申请", body: ["关联合同/柜位/品牌"], cls: "card blue" })}
${card({ x: 610, y: 180, w: 260, h: 80, title: "填写施工资料", body: ["图纸、审核材料、施工方信息"], cls: "card blue" })}
${card({ x: 610, y: 320, w: 260, h: 80, title: "图纸/材料审核", body: ["不通过退回补充"], cls: "card green" })}
${card({ x: 970, y: 320, w: 260, h: 80, title: "计算应缴费用", body: ["保证金、押金、工本费"], cls: "card amber" })}
${card({ x: 970, y: 460, w: 260, h: 80, title: "扫码缴费", body: ["工本费 + 保证金/押金"], cls: "card amber" })}
${card({ x: 1290, y: 460, w: 230, h: 80, title: "上传缴费凭证", body: ["可退项目填写退款账号"], cls: "card blue" })}
${card({ x: 1290, y: 600, w: 230, h: 80, title: "发放施工证", body: ["凭缴费凭证领取"], cls: "card green" })}
<path class="line" d="M500 220 H605"/><path class="line" d="M740 260 V315"/>
<path class="line" d="M870 360 H965"/><path class="line" d="M1100 400 V455"/>
<path class="line" d="M1230 500 H1285"/><path class="line" d="M1405 540 V595"/>
<rect x="180" y="740" width="430" height="70" class="card red"/><text class="label" x="205" y="775">可退费用</text><text class="body" x="205" y="800">施工保证金、施工押金：必须记录姓名、账号、开户行</text>
<rect x="660" y="740" width="360" height="70" class="card amber"/><text class="label" x="685" y="775">不可退费用</text><text class="body" x="685" y="800">施工证工本费：只留缴费凭证，不需要退款账号</text>
<rect x="1070" y="740" width="360" height="70" class="card blue"/><text class="label" x="1095" y="775">流程控制</text><text class="body" x="1095" y="800">未确认缴费和施工证，不允许进入施工报备</text>
</svg>`;

const night = `
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
${defs}${css}
${bg}
${header("夜间施工报备与安保执行流程", "把邮件汇总表转成系统报备、汇总、核验、归档的可追溯链路")}
${card({ x: 90, y: 170, w: 270, h: 120, title: "业务报备", body: ["施工日期、品牌/铺位", "施工方、负责人、人数", "施工事项、周期、措施"], cls: "card blue", no: 1 })}
${card({ x: 430, y: 170, w: 270, h: 120, title: "物业汇总", body: ["按日报表汇总", "形成夜间施工人员表", "发群/同步安保"], cls: "card purple", no: 2 })}
${card({ x: 770, y: 170, w: 270, h: 120, title: "安保核验", body: ["按汇总表确认人员", "核对施工证/负责人", "异常不放行"], cls: "card amber", no: 3 })}
${card({ x: 1110, y: 170, w: 270, h: 120, title: "签到进出场", body: ["纸质签字进场", "施工结束签离场时间", "纸质表上传归档"], cls: "card green", no: 4 })}
<path class="line" d="M360 230 H425"/><path class="line" d="M700 230 H765"/><path class="line" d="M1040 230 H1105"/>
<rect class="note" x="100" y="380" width="1380" height="350"/>
<text class="section-title" x="130" y="425">夜间施工人员汇总表字段建议</text>
<line x1="130" y1="455" x2="1450" y2="455" stroke="#d8dde8"/>
<text class="label" x="150" y="495">基础信息</text>
${lines(["日期、部门/品牌、装修厅房或地点、施工方名称", "现场负责人姓名、现场负责人联系方式"], 150, 530)}
<text class="label" x="570" y="495">施工信息</text>
${lines(["装修事项、人数、施工周期、影响区域", "采取措施、备注、是否需要保留配合"], 570, 530)}
<text class="label" x="990" y="495">现场执行</text>
${lines(["安保确认人、进场时间、离场时间", "异常说明、纸质签到表附件"], 990, 530)}
<rect x="130" y="640" width="1320" height="70" fill="#fff4da" stroke="#e3ad3f" rx="14"/>
<text class="label" x="160" y="682">控制点：未在当日汇总表内的施工人员，不允许夜间进场；纸质签到表作为现阶段现场依据，但系统必须留附件。</text>
</svg>`;

const refund = `
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
${defs}${css}
${bg}
${header("验收、退保证金与开柜流转", "迁移 OA 原流程：百货营运-23 品牌进(撤)场施工验收及保证金退还流程")}
${card({ x: 90, y: 170, w: 245, h: 125, title: "施工完成", body: ["业务/施工方提交完工", "关联原进场缴费流程"], cls: "card green", no: 1 })}
${card({ x: 395, y: 170, w: 245, h: 125, title: "现场验收", body: ["物业/工程现场确认", "纸质验收单签字"], cls: "card green", no: 2 })}
${card({ x: 700, y: 170, w: 245, h: 125, title: "发起退款", body: ["上传验收单、签到表", "带出原缴费金额"], cls: "card blue", no: 3 })}
${card({ x: 1005, y: 170, w: 245, h: 125, title: "扣款测算", body: ["管理费、水电费", "施工罚款、工本费"], cls: "card amber", no: 4 })}
${card({ x: 1310, y: 170, w: 245, h: 125, title: "财务退款", body: ["审核退款账号", "回填退款凭证"], cls: "card red", no: 5 })}
<path class="line" d="M335 232 H390"/><path class="line" d="M640 232 H695"/><path class="line" d="M945 232 H1000"/><path class="line" d="M1250 232 H1305"/>
<path class="dash" d="M1430 295 C1430 370 250 370 250 455"/>
${card({ x: 170, y: 455, w: 300, h: 125, title: "自动生成开柜流转单", body: ["来源：验收/退款完成", "避免业务重复发起"], cls: "card blue", no: 6 })}
${card({ x: 560, y: 455, w: 300, h: 125, title: "实测面积/用电功率", body: ["工程或物业填报", "形成测算依据"], cls: "card purple", no: 7 })}
${card({ x: 950, y: 455, w: 300, h: 125, title: "条款测算", body: ["电费条款、租金条款", "能耗/综合管理费"], cls: "card amber", no: 8 })}
${card({ x: 1340, y: 455, w: 220, h: 125, title: "ERP 更新", body: ["传 ERP 修改", "回填单号/截图"], cls: "card green", no: 9 })}
<path class="line" d="M470 518 H555"/><path class="line" d="M860 518 H945"/><path class="line" d="M1250 518 H1335"/>
<rect class="note" x="180" y="705" width="1240" height="95"/>
<text class="section-title" x="220" y="742">汇报口径</text>
${lines(["退保证金不是孤立流程，必须强关联原进场缴费流程；开柜流转单也不应人工重建，应该由验收/退款完成后自动生成。", "这样可以把扣款依据、退款凭证、实测面积、用电功率、ERP 条款更新全部串起来。"], 220, 775, "body", 26)}
</svg>`;

const files = [
  ["01-decoration-overview.svg", overview],
  ["02-entry-deposit-certificate.svg", entry],
  ["03-night-construction-report.svg", night],
  ["04-refund-opening-erp.svg", refund],
];

for (const [name, svg] of files) {
  writeFileSync(join(outDir, name), svg.trim() + "\n", "utf8");
}

writeFileSync(
  join(outDir, "README.md"),
  [
    "# 装修流程汇报图",
    "",
    "用于和领导介绍装修进撤场流程设计。",
    "",
    "- `01-decoration-overview.svg`：全流程总览",
    "- `02-entry-deposit-certificate.svg`：进场缴费与施工证领取",
    "- `03-night-construction-report.svg`：夜间施工报备与安保执行",
    "- `04-refund-opening-erp.svg`：验收、退保证金与开柜流转",
    "",
    "重新生成：",
    "",
    "```bash",
    "node docs/decoration-process-brief/generate-decoration-brief.mjs",
    "```",
    "",
  ].join("\n"),
  "utf8",
);

console.log(files.map(([name]) => join(outDir, name)).join("\n"));
