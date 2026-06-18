import pptxgen from "/Users/zhou/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs/dist/pptxgen.es.js";
import path from "node:path";
import fs from "node:fs";

const cwd = "/Users/zhou/Projects/ShopView";
const outDir = path.join(cwd, "reports");
const finalPath = path.join(outDir, "百货柜位管理系统上线汇报.pptx");
const imageDir = path.join(cwd, "reports/leader-images");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "ShopView";
pptx.company = "百货柜位管理系统";
pptx.subject = "项目进度、上线要求与收益地图建设路径";
pptx.title = "百货柜位管理系统上线汇报";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";
pptx.margin = 0;

const C = {
  ink: "0F172A",
  slate: "475569",
  muted: "64748B",
  line: "D9E2EC",
  bg: "F8FAFC",
  blue: "2563EB",
  teal: "0F766E",
  green: "16A34A",
  amber: "D97706",
  red: "DC2626",
  purple: "6D28D9",
  dark: "111827",
  white: "FFFFFF",
};

function slideBase(slide, title, kicker = "百货柜位管理系统") {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 0.14, fill: { color: C.teal }, line: { color: C.teal } });
  slide.addText(kicker, { x: 0.55, y: 0.33, w: 2.7, h: 0.22, fontSize: 8.5, color: C.muted, bold: true, margin: 0 });
  slide.addText(title, { x: 0.55, y: 0.58, w: 11.9, h: 0.55, fontSize: 24, bold: true, color: C.ink, margin: 0 });
}

function addFooter(slide, n) {
  slide.addText(`ShopView 项目汇报  |  ${String(n).padStart(2, "0")}`, {
    x: 0.55, y: 7.12, w: 2.4, h: 0.18, fontSize: 7.5, color: "94A3B8", margin: 0,
  });
}

function bodyText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h,
    fontFace: "Microsoft YaHei",
    fontSize: opts.fontSize ?? 13,
    color: opts.color ?? C.slate,
    bold: opts.bold ?? false,
    breakLine: false,
    fit: "shrink",
    valign: opts.valign ?? "mid",
    margin: opts.margin ?? 0.06,
    paraSpaceAfterPt: opts.paraSpaceAfterPt ?? 4,
    breakLine: false,
  });
}

function bulletList(slide, items, x, y, w, h, opts = {}) {
  const runs = [];
  for (const item of items) {
    runs.push({
      text: item,
      options: {
        bullet: { type: "ul" },
        hanging: 4,
        breakLine: true,
      },
    });
  }
  slide.addText(runs, {
    x, y, w, h,
    fontFace: "Microsoft YaHei",
    fontSize: opts.fontSize ?? 13.2,
    color: opts.color ?? C.slate,
    fit: "shrink",
    margin: 0.06,
    paraSpaceAfterPt: opts.space ?? 8,
    breakLine: false,
  });
}

function card(slide, x, y, w, h, title, body, color = C.blue) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: 0.05,
    fill: { color: C.white },
    line: { color: C.line, width: 1 },
    shadow: { type: "outer", color: "CBD5E1", opacity: 0.22, blur: 1, angle: 45, distance: 1 },
  });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.08, h, fill: { color }, line: { color } });
  bodyText(slide, title, x + 0.24, y + 0.16, w - 0.38, 0.28, { fontSize: 14.5, bold: true, color: C.ink });
  bodyText(slide, body, x + 0.24, y + 0.55, w - 0.38, h - 0.68, { fontSize: 10.8, color: C.slate, valign: "top" });
}

function stage(slide, x, y, w, h, no, title, body, color) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.04, fill: { color: "FFFFFF" }, line: { color: C.line, width: 1 } });
  slide.addShape(pptx.ShapeType.ellipse, { x: x + 0.18, y: y + 0.18, w: 0.48, h: 0.48, fill: { color }, line: { color } });
  slide.addText(no, { x: x + 0.18, y: y + 0.29, w: 0.48, h: 0.18, fontSize: 10.5, bold: true, color: C.white, align: "center", margin: 0 });
  bodyText(slide, title, x + 0.78, y + 0.18, w - 0.95, 0.28, { fontSize: 13.2, bold: true, color: C.ink });
  bodyText(slide, body, x + 0.78, y + 0.58, w - 0.95, h - 0.7, { fontSize: 10.2, color: C.slate, valign: "top" });
}

function metric(slide, x, y, value, label, color) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w: 2.05, h: 0.76, rectRadius: 0.04, fill: { color }, line: { color } });
  slide.addText(value, { x: x + 0.12, y: y + 0.1, w: 1.8, h: 0.28, fontSize: 17, bold: true, color: C.white, margin: 0 });
  slide.addText(label, { x: x + 0.12, y: y + 0.43, w: 1.8, h: 0.18, fontSize: 8.8, color: "E0F2FE", margin: 0 });
}

function imageFull(slide, file, x, y, w, h) {
  const p = path.join(imageDir, file);
  if (fs.existsSync(p)) slide.addImage({ path: p, x, y, w, h });
}

// 1 Cover
{
  const slide = pptx.addSlide();
  slide.background = { color: "F8FAFC" };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: "F8FAFC" }, line: { color: "F8FAFC" } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 4.2, h: 7.5, fill: { color: "0F172A" }, line: { color: "0F172A" } });
  slide.addText("ShopView", { x: 0.62, y: 0.58, w: 2, h: 0.25, fontSize: 13, color: "99F6E4", bold: true, margin: 0 });
  slide.addText("百货柜位管理系统", { x: 0.62, y: 1.42, w: 3.05, h: 0.88, fontSize: 29, bold: true, color: C.white, fit: "shrink", margin: 0 });
  slide.addText("项目进度、上线要求与收益地图建设路径", { x: 0.62, y: 2.48, w: 3.0, h: 0.78, fontSize: 15.5, color: "CBD5E1", fit: "shrink", margin: 0 });
  slide.addText("汇报对象：公司领导 / 老板经营决策视角", { x: 0.62, y: 6.55, w: 3.0, h: 0.24, fontSize: 10, color: "94A3B8", margin: 0 });
  imageFull(slide, "03-revenue-map-square.png", 4.68, 0.62, 7.95, 6.2);
}

// 2 Executive message
{
  const slide = pptx.addSlide();
  slideBase(slide, "核心结论：收益地图是老板视角的最终成果，但上线必须先固化数据底座");
  bodyText(slide, "建议采用“基础模块先试运行，收益地图后正式上线，招商规划再延伸”的节奏。这样既能尽快让业务部门用起来，也能保证后续给老板看的收益地图有销售、合同、结算和柜位关系作为依据。", 0.78, 1.35, 11.7, 0.68, { fontSize: 16, bold: true, color: C.ink, valign: "top" });
  card(slide, 0.78, 2.28, 3.72, 2.45, "不是先做一张图", "如果销售、合同、柜位绑定还未校验，收益地图容易变成展示图，后续数据解释压力会很大。", C.red);
  card(slide, 4.82, 2.28, 3.72, 2.45, "先让基础数据跑起来", "销售、活动分析、合同模块先上线，让业务和财务在真实使用中发现口径和数据问题。", C.blue);
  card(slide, 8.86, 2.28, 3.72, 2.45, "再形成老板看板", "基础数据稳定后，收益地图可以支撑低效铺位、招商调整、业态规划和收益提升测算。", C.green);
  slide.addShape(pptx.ShapeType.roundRect, { x: 1.28, y: 5.45, w: 10.78, h: 0.62, rectRadius: 0.03, fill: { color: "0F172A" }, line: { color: "0F172A" } });
  bodyText(slide, "汇报口径：先上线可用模块，边使用边修正；收益地图作为第二阶段成果，最终服务老板经营决策。", 1.6, 5.59, 10.1, 0.27, { fontSize: 14.2, bold: true, color: C.white });
  addFooter(slide, 2);
}

// 3 Why: manual pain
{
  const slide = pptx.addSlide();
  slideBase(slide, "为什么要做：替代每月“CAD制图 + 财务汇总表”的重复人工链条");
  slide.addShape(pptx.ShapeType.rect, { x: 0.75, y: 1.42, w: 12, h: 0.02, fill: { color: C.line }, line: { color: C.line } });
  stage(slide, 0.9, 1.85, 2.75, 1.45, "01", "业务部门手工画图", "每月在 CAD 上维护柜位、品牌、业态和位置变化。", C.blue);
  stage(slide, 3.9, 1.85, 2.75, 1.45, "02", "财务手工汇总", "销售、合同、租金、联营、费用等多张表分散汇总。", C.amber);
  stage(slide, 6.9, 1.85, 2.75, 1.45, "03", "人工匹配图表", "把汇总表和柜位图人工对应，容易受人员经验影响。", C.purple);
  stage(slide, 9.9, 1.85, 2.75, 1.45, "04", "形成静态汇报图", "老板能看到结果，但很难继续下钻合同、销售和收益来源。", C.red);
  slide.addShape(pptx.ShapeType.roundRect, { x: 1.0, y: 4.38, w: 11.35, h: 1.45, rectRadius: 0.04, fill: { color: "FEF2F2" }, line: { color: "FECACA" } });
  bodyText(slide, "当前痛点", 1.32, 4.65, 1.3, 0.28, { fontSize: 15, bold: true, color: C.red });
  bulletList(slide, ["每月重复劳动，图纸和数据都要重新加工", "图纸、合同、销售、收益口径容易不一致", "静态图无法解释明细，也难以支持招商规划测算"], 2.55, 4.55, 9.35, 0.92, { fontSize: 12.6, color: C.ink, space: 4 });
  addFooter(slide, 3);
}

// 4 Boss value
{
  const slide = pptx.addSlide();
  slideBase(slide, "老板真正需要的不是系统页面，而是可解释、可追溯、可推演的经营决策图");
  slide.addShape(pptx.ShapeType.roundRect, { x: 0.78, y: 1.52, w: 4.0, h: 4.8, rectRadius: 0.04, fill: { color: "0F172A" }, line: { color: "0F172A" } });
  bodyText(slide, "老板视角", 1.08, 1.9, 2.4, 0.35, { fontSize: 20, bold: true, color: C.white });
  bulletList(slide, ["哪些铺位赚钱，哪些铺位低效？", "低效铺位为什么低效？", "调整品牌或业态能提升多少？", "招商优先级应该怎么排？", "规划调整有没有数据依据？"], 1.15, 2.52, 3.2, 2.8, { fontSize: 14, color: "E2E8F0", space: 9 });
  slide.addShape(pptx.ShapeType.chevron, { x: 5.1, y: 3.28, w: 0.78, h: 0.58, fill: { color: C.teal }, line: { color: C.teal } });
  card(slide, 6.15, 1.45, 2.9, 1.28, "看现状", "收益地图自动染色，识别低效、空置、重点铺位。", C.green);
  card(slide, 9.45, 1.45, 2.9, 1.28, "看原因", "点击铺位钻取销售、合同、结算、活动明细。", C.blue);
  card(slide, 6.15, 3.08, 2.9, 1.28, "做判断", "按业态、品牌、楼层、坪效对比经营表现。", C.amber);
  card(slide, 9.45, 3.08, 2.9, 1.28, "推方案", "支撑招商调整、铺位替换和收益提升测算。", C.purple);
  slide.addShape(pptx.ShapeType.roundRect, { x: 6.15, y: 5.08, w: 6.2, h: 0.82, rectRadius: 0.04, fill: { color: "ECFEFF" }, line: { color: "A5F3FC" } });
  bodyText(slide, "建设重点：先保证数据可信，再把收益地图升级为老板经营决策入口。", 6.42, 5.34, 5.65, 0.26, { fontSize: 13.5, bold: true, color: C.teal });
  addFooter(slide, 4);
}

// 5 Current progress visual
{
  const slide = pptx.addSlide();
  slideBase(slide, "当前建设进度：系统已形成从空间、台账到分析的基础框架");
  imageFull(slide, "01-function-overview-square.png", 0.25, 0.95, 6.55, 5.95);
  slide.addText("已具备基础", { x: 7.2, y: 1.38, w: 2.2, h: 0.32, fontSize: 17, bold: true, color: C.ink, margin: 0 });
  bulletList(slide, ["楼层、底图、柜位图版本、经营单元", "合同台账、合同详情、合同柜位绑定", "销售看板、商品明细、小票明细", "活动分析、凭证匹配、会员活动分析", "用户角色、数据范围、企微规则、审计日志"], 7.28, 1.88, 4.8, 2.35, { fontSize: 12.4, space: 7 });
  slide.addText("需继续验证", { x: 7.2, y: 4.6, w: 2.2, h: 0.32, fontSize: 17, bold: true, color: C.ink, margin: 0 });
  bulletList(slide, ["真实销售数据完整性", "合同与柜位绑定准确性", "活动和凭证匹配口径", "收益指标与结算来源", "权限范围是否符合管理边界"], 7.28, 5.1, 4.8, 1.35, { fontSize: 12.4, space: 6 });
  addFooter(slide, 5);
}

// 6 Launch route
{
  const slide = pptx.addSlide();
  slideBase(slide, "建议上线路径：先试运行基础模块，再上线收益地图，最后延伸招商规划");
  imageFull(slide, "02-business-loop-square.png", 0.35, 1.05, 6.2, 5.55);
  stage(slide, 6.95, 1.22, 5.28, 0.92, "1", "基础模块试运行", "销售看板、商品明细、活动分析、凭证匹配、合同台账、合同柜位绑定先上线。", C.blue);
  stage(slide, 6.95, 2.45, 5.28, 0.92, "2", "数据口径修正", "让业务、财务在真实使用中发现销售、合同、柜位、权限问题，及时处理。", C.teal);
  stage(slide, 6.95, 3.68, 5.28, 0.92, "3", "收益地图上线", "铺位收益汇总、地图自动染色、点击钻取明细，逐步替代手工图表。", C.green);
  stage(slide, 6.95, 4.91, 5.28, 0.92, "4", "招商规划延伸", "做低效铺位治理、业态调整、品牌替换和收益提升测算。", C.purple);
  addFooter(slide, 6);
}

// 7 Phase one
{
  const slide = pptx.addSlide();
  slideBase(slide, "第一阶段上线范围：让业务和财务先用起来，用真实使用校验数据");
  const cols = [
    ["销售模块", "销售看板\n商品销售明细\n小票与付款明细", C.blue],
    ["活动分析", "通用活动分析\n凭证匹配\n会员活动分析", C.amber],
    ["合同模块", "合同台账\n合同详情\n合同柜位绑定", C.green],
    ["基础支撑", "供应商/柜位定义\n用户权限\n登录与操作日志", C.purple],
  ];
  cols.forEach(([t, b, c], i) => card(slide, 0.75 + i * 3.12, 1.52, 2.72, 2.25, t, b, c));
  slide.addShape(pptx.ShapeType.roundRect, { x: 1.05, y: 4.42, w: 11.25, h: 1.18, rectRadius: 0.04, fill: { color: "ECFDF5" }, line: { color: "BBF7D0" } });
  bodyText(slide, "第一阶段目标", 1.35, 4.72, 1.8, 0.28, { fontSize: 15.2, bold: true, color: C.green });
  bodyText(slide, "不是一次性把收益地图做满，而是先把销售、合同、活动、权限这些基础数据跑顺；使用中发现问题，及时修正，为后续收益地图提供可信数据。", 3.12, 4.63, 8.72, 0.42, { fontSize: 13.5, bold: true, color: C.ink });
  addFooter(slide, 7);
}

// 8 Revenue map requirements
{
  const slide = pptx.addSlide();
  slideBase(slide, "收益地图上线前置条件：数据可信，图才可信");
  imageFull(slide, "03-revenue-map-square.png", 0.25, 1.0, 6.42, 5.85);
  const reqs = [
    ["销售口径", "按门店、楼层、柜组、经营单元能查，退货/冲销等规则清楚。"],
    ["合同绑定", "供应商、合同、柜组、柜位关系准确，重复编码有门店/楼层上下文。"],
    ["结算来源", "联营、租赁、保底、扣点、费用等取数来源和周期明确。"],
    ["地图规则", "颜色分段、低效铺位、空置铺位、重点铺位判断标准明确。"],
    ["责任闭环", "业务和财务认可基础数据，异常能定位到数据源或绑定关系。"],
  ];
  reqs.forEach((r, i) => {
    slide.addShape(pptx.ShapeType.roundRect, { x: 7.05, y: 1.35 + i * 0.92, w: 5.45, h: 0.62, rectRadius: 0.03, fill: { color: i % 2 ? "FFFFFF" : "F1F5F9" }, line: { color: C.line } });
    bodyText(slide, r[0], 7.28, 1.49 + i * 0.92, 1.1, 0.2, { fontSize: 11.8, bold: true, color: C.teal });
    bodyText(slide, r[1], 8.38, 1.42 + i * 0.92, 3.85, 0.34, { fontSize: 10.4, color: C.slate });
  });
  slide.addShape(pptx.ShapeType.roundRect, { x: 7.05, y: 6.02, w: 5.45, h: 0.52, rectRadius: 0.03, fill: { color: "0F172A" }, line: { color: "0F172A" } });
  bodyText(slide, "上线原则：收益地图可以先小范围试点，不建议在基础口径未稳定前全量承诺。", 7.32, 6.18, 4.9, 0.18, { fontSize: 11.4, bold: true, color: C.white });
  addFooter(slide, 8);
}

// 9 Data and permission
{
  const slide = pptx.addSlide();
  slideBase(slide, "上线保障：ERP/POS 数据、系统权限和审计日志要同步推进");
  imageFull(slide, "04-data-permission-square.png", 0.32, 1.02, 6.25, 5.72);
  card(slide, 6.98, 1.35, 2.55, 1.22, "数据源稳定", "ERP 合同、供应商、POS 销售、结算单同步规则明确。", C.blue);
  card(slide, 9.85, 1.35, 2.55, 1.22, "权限边界清楚", "按用户、角色、门店、部门、业务范围控制可见数据。", C.teal);
  card(slide, 6.98, 2.9, 2.55, 1.22, "异常可追溯", "登录日志、操作日志、模块访问记录帮助定位问题。", C.amber);
  card(slide, 9.85, 2.9, 2.55, 1.22, "使用有反馈", "业务和财务试用后反馈口径、数据和功能问题。", C.green);
  slide.addShape(pptx.ShapeType.roundRect, { x: 7.1, y: 5.15, w: 5.18, h: 0.78, rectRadius: 0.03, fill: { color: "FEFCE8" }, line: { color: "FDE68A" } });
  bodyText(slide, "要求：上线不只看页面能否打开，更要看数据来源、权限范围、异常追踪和业务反馈机制是否准备好。", 7.38, 5.39, 4.65, 0.25, { fontSize: 12.2, bold: true, color: C.ink });
  addFooter(slide, 9);
}

// 10 Decision request
{
  const slide = pptx.addSlide();
  slideBase(slide, "需要领导确认的上线决策");
  metric(slide, 0.9, 1.45, "先试运行", "销售 / 活动 / 合同基础模块", C.blue);
  metric(slide, 3.35, 1.45, "再上地图", "收益地图依赖数据口径稳定", C.green);
  metric(slide, 5.8, 1.45, "最终决策", "招商规划 / 铺位替换测算", C.purple);
  slide.addShape(pptx.ShapeType.roundRect, { x: 8.55, y: 1.28, w: 3.85, h: 1.1, rectRadius: 0.04, fill: { color: "0F172A" }, line: { color: "0F172A" } });
  bodyText(slide, "建议批准：第一阶段上线试运行", 8.9, 1.62, 3.18, 0.28, { fontSize: 15.2, bold: true, color: C.white });

  const decisions = [
    ["上线范围", "销售看板、商品销售明细、活动分析、凭证匹配、合同台账、合同柜位绑定、权限日志。"],
    ["试运行对象", "业务部门、财务相关人员、管理人员分角色试用，发现问题及时反馈。"],
    ["验收重点", "数据准确、合同绑定准确、权限范围正确、异常可定位、业务能真实使用。"],
    ["收益地图节奏", "基础数据稳定后再正式上线收益地图，并逐步扩展招商规划和测算能力。"],
  ];
  decisions.forEach((d, i) => {
    slide.addShape(pptx.ShapeType.roundRect, { x: 1.0, y: 3.02 + i * 0.76, w: 11.25, h: 0.54, rectRadius: 0.03, fill: { color: i % 2 ? "FFFFFF" : "F1F5F9" }, line: { color: C.line } });
    bodyText(slide, d[0], 1.28, 3.17 + i * 0.76, 1.25, 0.18, { fontSize: 11.5, bold: true, color: C.teal });
    bodyText(slide, d[1], 2.58, 3.12 + i * 0.76, 9.35, 0.26, { fontSize: 11.4, color: C.ink });
  });
  slide.addText("汇报结论", { x: 1.0, y: 6.25, w: 1.2, h: 0.22, fontSize: 11, bold: true, color: C.muted, margin: 0 });
  bodyText(slide, "第一阶段先让基础模块进入真实使用，沉淀可信数据；收益地图作为第二阶段老板看板上线，最终延伸到招商规划和经营决策。", 2.02, 6.18, 9.9, 0.35, { fontSize: 13.2, bold: true, color: C.ink });
  addFooter(slide, 10);
}

await pptx.writeFile({ fileName: finalPath });
console.log(finalPath);
