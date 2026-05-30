import { unstable_noStore as noStore } from "next/cache"
import { executeOracle } from "@/lib/oracle"
import { getActiveStore, getPaymentStores, type StoreOption } from "@/lib/stores"

type InvoiceRow = {
  ID: string | number
  INVOICE_NO: string
  INVOICE_TYPE_NAME: string | null
  IS_RED_INVOICE: string | null
  ISSUE_DATE: Date | string
  SELLER_NAME: string | null
  BUYER_NAME: string | null
  SELLER_TAX_NO: string | null
  BUYER_TAX_NO: string | null
  AMOUNT_EXCL_TAX: number | null
  TAX_AMOUNT: number | null
  AMOUNT_INCL_TAX: number | null
  SOURCE_SYSTEM: string | null
  MATCH_ID: string | null
  TARGET_OBJECT_TYPE: string | null
  TARGET_NO: string | null
  MATCH_STATUS: string | null
  MATCH_SCORE: number | null
  MANUAL_CONFIRM_FLAG: string | null
  DIFF_AMOUNT: number | null
  SPHBILLNO: string | null
  OA_SPHBILLNO: string | null
  MANUAL_DOC_NO: string | null
  SUPPLIER_NAME: string | null
  PAYMENT_AMOUNT: number | null
  BUSINESS_TYPE: string | null
  PAYMENT_CREATE_TIME: Date | string | null
  REMARK: string | null
}

type CountRow = {
  TOTAL: number
}

type InvoiceSummaryRow = {
  MATCHED: number
  AMOUNT_MISMATCH: number
  UNMATCHED: number
  ARCHIVED: number
}

type PaymentBillSummaryRow = {
  TOTAL: number
  COMPLETED: number
  PARTIAL: number
  PENDING: number
  TOTAL_AMOUNT: number | null
  LINKED_INVOICES: number | null
}

type DashboardMonthlyInvoiceRow = {
  MONTH_NO: string
  MATCHED: number | null
  AMOUNT_MISMATCH: number | null
  UNMATCHED: number | null
  ARCHIVED: number | null
}

type DashboardMonthlyPaymentRow = {
  MONTH_NO: string
  TOTAL: number | null
}

export type InvoiceListItem = {
  id: string
  invoiceNo: string
  sellerName: string
  buyerName: string
  sellerTaxNo?: string
  buyerTaxNo?: string
  invoiceDate: string
  matchedDocDate: string
  amount: number
  taxAmount: number
  totalAmount: number
  isRedInvoice: boolean
  matchStatus: "matched" | "amount_mismatch" | "unmatched" | "archived"
  source: string
  documentSource: string
  matchedDoc: string
  matchedDocAmount: number
  docType: string
  matchScore: number
  remark: string
}

export type PaymentBillItem = {
  id: string
  source: string
  docType: string
  docNo: string
  partner: string
  storeId: string
  storeName: string
  storeTaxNo?: string
  businessDate: string
  amount: number
  matchedAmount: number
  remainingAmount: number
  linkedInvoices: number
  linkedTransactions: number
  status: "completed" | "partial" | "pending"
}

/** OA 鍗曟嵁鍒楄〃椤癸紱鏁版嵁鏉ヨ嚜 ETLKP.OA_BILL锛堥儴闂ㄥ垪鐢?OA_BILL_DEPT_EXPR 绛夌幆澧冨彉閲忓榻愬疄闄呰〃缁撴瀯锛夈€?*/
export type OaBillItem = {
  id: string
  docType: string
  docNo: string
  storeId: string
  storeName: string
  applicant: string
  supplierName: string
  department: string
  businessDate: string
  amount: number
  linkedInvoices: number
  linkedTransactions: number
  status: "completed" | "partial" | "pending"
  linkedInvoiceItems: OaLinkedInvoiceItem[]
}

export type OaLinkedInvoiceItem = {
  id: string
  invoiceNo: string
  sellerName: string
  buyerName: string
  invoiceDate: string
  amount: number
  matchStatus: string
  matchScore: number
  diffAmount: number
  manualConfirmed: boolean
}

export type DashboardData = {
  stats: {
    matchedPending: number
    amountMismatch: number
    unmatched: number
    confirmed: number
    paymentBills: number
  }
  recentActivities: {
    id: string
    type: "invoice" | "document" | "alert"
    action: string
    detail: string
    time: string
    status: "success" | "warning" | "info"
  }[]
  monthlySummary: {
    month: string
    matchedPending: number
    amountMismatch: number
    unmatched: number
    confirmed: number
    paymentBills: number
  }[]
}

export type InvoiceSummary = {
  matched: number
  amountMismatch: number
  unmatched: number
  archived: number
}

export type PaymentBillSummary = {
  total: number
  completed: number
  partial: number
  pending: number
  totalAmount: number
  linkedInvoices: number
}

export type PageResult<T> = {
  items: T[]
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export const DEFAULT_PAGE_SIZE = 50

const matchedInvoiceAmountSql =
  "sum(case when ih.is_red_invoice = 'Y' then -abs(nvl(ih.amount_incl_tax, 0)) else nvl(ih.amount_incl_tax, 0) end)"

/** Next.js searchParams 鍚屼竴 key 鍙兘鍑虹幇 string[]锛岀粺涓€鍙栭椤归伩鍏?.trim 绛夎繍琛屾椂寮傚父銆?*/
export function firstQueryString(value: string | string[] | undefined): string | undefined {
  if (value === undefined) return undefined
  const v = Array.isArray(value) ? value[0] : value
  return typeof v === "string" ? v : undefined
}

function normalizePage(page: number | string | string[] | undefined) {
  const value =
    typeof page === "number"
      ? page
      : Number(firstQueryString(page as string | string[] | undefined))
  if (!Number.isFinite(value) || value < 1) return 1
  return Math.floor(value)
}

function pageResult<T>(
  items: T[],
  total: number,
  page: number,
  pageSize: number
): PageResult<T> {
  return {
    items,
    page,
    pageSize,
    total,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
  }
}

function formatDate(value: Date | string | null | undefined) {
  if (!value) return "-"
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function toNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return 0
  return Number(value)
}

function invoiceAmount(row: InvoiceRow, value: number | string | null | undefined) {
  const amount = toNumber(value)
  return row.IS_RED_INVOICE === "Y" ? -Math.abs(amount) : amount
}

function normalizeSearch(value: string | string[] | undefined) {
  const trimmed = firstQueryString(value)?.trim()
  return trimmed ? trimmed : undefined
}

const YEAR_MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/

function normalizeYearMonth(value: string | string[] | undefined) {
  const trimmed = firstQueryString(value)?.trim()
  if (!trimmed || trimmed === "all") return undefined
  return YEAR_MONTH_RE.test(trimmed) ? trimmed : undefined
}

function invoiceStoreWhere(store: StoreOption | undefined, paymentAlias = "pb") {
  if (!store) return ""

  if (store.taxNo) {
    return ` and (
      trim(ih.buyer_tax_no) = :activeStoreTaxNo
      or trim(ih.seller_tax_no) = :activeStoreTaxNo
      or (
        ih.buyer_tax_no is null
        and trim(ih.buyer_name) = :activeStoreName
      )
      or (
        ih.seller_tax_no is null
        and trim(ih.seller_name) = :activeStoreName
      )
      or ${paymentAlias}.store_id = :activeStoreId
    )`
  }

  return ` and (
    trim(ih.buyer_name) = :activeStoreName
    or trim(ih.seller_name) = :activeStoreName
    or ${paymentAlias}.store_id = :activeStoreId
  )`
}

function invoiceNameStoreWhere(store: StoreOption | undefined) {
  if (!store) return ""

  if (store.taxNo) {
    return ` and (
      trim(ih.buyer_tax_no) = :activeStoreTaxNo
      or trim(ih.seller_tax_no) = :activeStoreTaxNo
      or (
        ih.buyer_tax_no is null
        and trim(ih.buyer_name) = :activeStoreName
      )
      or (
        ih.seller_tax_no is null
        and trim(ih.seller_name) = :activeStoreName
      )
    )`
  }

  return ` and (
    trim(ih.buyer_name) = :activeStoreName
    or trim(ih.seller_name) = :activeStoreName
  )`
}

function paymentBillStoreWhere(store: StoreOption | undefined) {
  if (!store) return ""

  return ` and (
    pb.store_id = :activeStoreId
    or trim(psn.store_name) = :activeStoreName
  )`
}

function storeBinds(store: StoreOption | undefined, includeTaxNo = false) {
  return store
    ? {
        activeStoreId: store.id,
        activeStoreName: store.name,
        ...(includeTaxNo && store.taxNo ? { activeStoreTaxNo: store.taxNo } : {}),
      }
    : {}
}

function invoiceStatus(row: InvoiceRow): InvoiceListItem["matchStatus"] {
  if (!row.MATCH_ID) return "unmatched"
  if (Math.abs(toNumber(row.DIFF_AMOUNT)) > 0) return "amount_mismatch"
  if (row.MANUAL_CONFIRM_FLAG === "Y") return "archived"
  return "matched"
}

function documentSourceLabel(row: InvoiceRow) {
  const type = row.TARGET_OBJECT_TYPE?.trim().toUpperCase() ?? ""
  if (type.includes("MANUAL") || type.includes("手工")) return "手工补录"
  if (type.includes("OA") || type.includes("报销")) return "OA"
  if (type.includes("PAYMENT") || type.includes("付款")) return "付款单"
  if (row.MANUAL_DOC_NO) return "手工补录"
  if (row.OA_SPHBILLNO) return "OA"
  if (row.SPHBILLNO) return "付款单"
  return row.TARGET_OBJECT_TYPE || "-"
}

function matchedDocType(row: InvoiceRow) {
  const source = documentSourceLabel(row)
  if (source === "手工补录") {
    return row.BUSINESS_TYPE ? `手工补录(${row.BUSINESS_TYPE})` : "手工补录"
  }
  if (source === "OA") {
    return row.BUSINESS_TYPE ? `OA单据(${row.BUSINESS_TYPE})` : "OA单据"
  }
  return row.BUSINESS_TYPE ? `付款单(${row.BUSINESS_TYPE})` : "付款单"
}

function mapInvoice(row: InvoiceRow): InvoiceListItem {
  return {
    id: String(row.ID),
    invoiceNo: row.INVOICE_NO,
    sellerName: row.SELLER_NAME || "-",
    buyerName: row.BUYER_NAME || "-",
    sellerTaxNo: row.SELLER_TAX_NO?.trim() || undefined,
    buyerTaxNo: row.BUYER_TAX_NO?.trim() || undefined,
    invoiceDate: formatDate(row.ISSUE_DATE),
    matchedDocDate: formatDate(row.PAYMENT_CREATE_TIME),
    amount: invoiceAmount(row, row.AMOUNT_EXCL_TAX),
    taxAmount: invoiceAmount(row, row.TAX_AMOUNT),
    totalAmount: invoiceAmount(row, row.AMOUNT_INCL_TAX),
    isRedInvoice: row.IS_RED_INVOICE === "Y",
    matchStatus: invoiceStatus(row),
    source: row.SOURCE_SYSTEM || "-",
    documentSource: documentSourceLabel(row),
    matchedDoc: row.SPHBILLNO || row.OA_SPHBILLNO || row.MANUAL_DOC_NO || row.TARGET_NO || "-",
    matchedDocAmount: toNumber(row.PAYMENT_AMOUNT),
    docType: matchedDocType(row),
    matchScore: Math.round(toNumber(row.MATCH_SCORE)),
    remark: row.REMARK || "-",
  }
}

const invoiceFromSql = `
  from (
    select
      to_char(ih.id) id,
      ih.invoice_no,
      ih.invoice_type_name,
      ih.is_red_invoice,
      ih.issue_date,
      ih.seller_name,
      ih.buyer_name,
      ih.seller_tax_no,
      ih.buyer_tax_no,
      ih.amount_excl_tax,
      ih.tax_amount,
      ih.amount_incl_tax,
      ih.source_system,
      mr.id match_id,
      mr.target_object_type,
      mr.target_no,
      mr.match_status,
      mr.match_score,
      mr.manual_confirm_flag,
      mr.diff_amount,
      mr.create_time match_create_time,
      pb.sphbillno,
      ob.sphbillno oa_sphbillno,
      case
        when upper(trim(mr.target_object_type)) like '%MANUAL%' then mr.target_no
        else null
      end manual_doc_no,
      coalesce(pb.supplier_name, ob.supplier_name) supplier_name,
      coalesce(pb.payment_amount, ob.payment_amount, mr.match_amount) payment_amount,
      coalesce(pb.business_type, ob.type_01, mb.business_type) business_type,
      coalesce(pb.create_time, ob.create_time, mb.business_date, mr.create_time) payment_create_time,
      coalesce(mb.remark, mr.remark) remark
    from ETLKP.INVOICE_HEADER ih
    left join (
      select *
      from (
        select mr.*,
               row_number() over (
                 partition by mr.header_id
                 order by mr.update_time desc nulls last, mr.create_time desc nulls last
               ) rn
        from ETLKP.INVOICE_MATCH_RECORD_ZJB mr
        where nvl(mr.is_deleted, '0') <> '1'
      )
      where rn = 1
    ) mr on mr.header_id = to_char(ih.id)
    left join ETLKP.PAYMENT_BILL pb
      on pb.id = mr.target_object_id
     and nvl(pb.is_deleted, '0') <> '1'
    left join ETLKP.OA_BILL ob
      on trim(to_char(ob.id)) = trim(mr.target_object_id)
     and nvl(ob.is_deleted, '0') <> '1'
    left join ETLKP.MANUAL_BUSINESS_BILL mb
      on trim(mb.id) = trim(mr.target_object_id)
     and nvl(mb.is_deleted, '0') <> '1'
    where nvl(ih.is_deleted, '0') <> '1'
`

async function getInvoicePage(
  options: {
    page?: number | string
    pageSize?: number
    where?: string
    orderBy?: string
    supplierName?: string
    status?: string
    yearMonth?: string
    yearMonthField?: "invoice" | "payment"
  } = {}
) {
  noStore()
  const requestedPage = normalizePage(options.page)
  const pageSize = options.pageSize ?? DEFAULT_PAGE_SIZE
  const where = options.where ?? ""
  const orderBy = options.orderBy ?? "issue_date desc, id desc"
  const supplierName = normalizeSearch(options.supplierName)
  const ym = normalizeYearMonth(options.yearMonth)
  const yearMonthField = options.yearMonthField ?? "invoice"
  const dateWhere = ym
    ? yearMonthField === "payment"
      ? ` and to_char(coalesce(pb.create_time, ob.create_time, mb.business_date, mr.create_time), 'yyyy-mm') = :yearMonth`
      : ` and to_char(ih.issue_date, 'yyyy-mm') = :yearMonth`
    : ""
  const activeStore = await getActiveStore()
  const storeWhere = invoiceStoreWhere(activeStore)
  const supplierWhere = supplierName
    ? ` and (
          ih.seller_name like '%' || :supplierName || '%'
          or ih.buyer_name like '%' || :supplierName || '%'
          or ih.invoice_no like '%' || :supplierName || '%'
          or mr.target_no like '%' || :supplierName || '%'
          or pb.sphbillno like '%' || :supplierName || '%'
          or ob.sphbillno like '%' || :supplierName || '%'
          or ob.supplier_name like '%' || :supplierName || '%'
          or mb.doc_no like '%' || :supplierName || '%'
          or mb.partner_name like '%' || :supplierName || '%'
        )`
    : ""
  const statusWhere =
    options.status === "matched"
      ? " and mr.id is not null and nvl(mr.manual_confirm_flag, 'N') <> 'Y' and abs(nvl(mr.diff_amount, 0)) = 0"
      : options.status === "amount_mismatch"
        ? " and mr.id is not null and abs(nvl(mr.diff_amount, 0)) > 0"
        : options.status === "unmatched"
          ? ` and not exists (
              select 1
              from ETLKP.INVOICE_MATCH_RECORD_ZJB status_mr
              where status_mr.header_id = to_char(ih.id)
                and nvl(status_mr.is_deleted, '0') <> '1'
            )`
          : options.status === "archived"
            ? " and mr.id is not null and mr.manual_confirm_flag = 'Y' and abs(nvl(mr.diff_amount, 0)) = 0"
            : ""
  const totalRows = await executeOracle<CountRow>(
    `select count(*) total ${invoiceFromSql} ${where} ${supplierWhere} ${statusWhere} ${dateWhere} ${storeWhere})`,
    {
      ...(supplierName ? { supplierName } : {}),
      ...(ym ? { yearMonth: ym } : {}),
      ...storeBinds(activeStore, true),
    }
  )
  const total = toNumber(totalRows[0]?.TOTAL)
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const page = Math.min(requestedPage, totalPages)
  const offset = (page - 1) * pageSize
  const binds: Record<string, string | number> = { offset, endRow: offset + pageSize }
  if (supplierName) binds.supplierName = supplierName
  if (ym) binds.yearMonth = ym
  Object.assign(binds, storeBinds(activeStore, true))
  const rows = await executeOracle<InvoiceRow>(
    `select *
     from (
       select data_rows.*, row_number() over (order by ${orderBy}) rn
       ${invoiceFromSql}
       ${where}
       ${supplierWhere}
       ${statusWhere}
       ${dateWhere}
       ${storeWhere}
     ) data_rows
    )
     where rn > :offset and rn <= :endRow
     order by rn`,
    binds
  )

  return pageResult(rows.map(mapInvoice), total, page, pageSize)
}

export async function getInvoices(
  page?: number | string,
  pageSize = DEFAULT_PAGE_SIZE,
  supplierName?: string,
  status?: string,
  yearMonth?: string
) {
  return getInvoicePage({ page, pageSize, supplierName, status, yearMonth })
}

export async function getInvoiceSummary(
  supplierName?: string,
  yearMonth?: string
): Promise<InvoiceSummary> {
  noStore()
  const supplier = normalizeSearch(supplierName)
  const ym = normalizeYearMonth(yearMonth)
  const activeStore = await getActiveStore()
  const storeWhere = invoiceStoreWhere(activeStore)
  const supplierWhere = supplier
    ? ` and (
          ih.seller_name like '%' || :supplierName || '%'
          or ih.buyer_name like '%' || :supplierName || '%'
        )`
    : ""
  const dateWhere = ym
    ? ` and to_char(coalesce(pb.create_time, ob.create_time, mb.business_date, mr.create_time, ih.issue_date), 'yyyy-mm') = :yearMonth`
    : ""
  const rows = await executeOracle<InvoiceSummaryRow>(
    `select
       sum(case when match_id is not null and abs(nvl(diff_amount, 0)) = 0 and nvl(manual_confirm_flag, 'N') <> 'Y' then 1 else 0 end) matched,
       sum(case when match_id is not null and abs(nvl(diff_amount, 0)) > 0 then 1 else 0 end) amount_mismatch,
       sum(case when match_id is null then 1 else 0 end) unmatched,
       sum(case when match_id is not null and abs(nvl(diff_amount, 0)) = 0 and manual_confirm_flag = 'Y' then 1 else 0 end) archived
     ${invoiceFromSql}
     ${supplierWhere}
     ${dateWhere}
     ${storeWhere}
    )`,
    {
      ...(supplier ? { supplierName: supplier } : {}),
      ...(ym ? { yearMonth: ym } : {}),
      ...storeBinds(activeStore, true),
    }
  )
  const summary = rows[0]

  return {
    matched: toNumber(summary?.MATCHED),
    amountMismatch: toNumber(summary?.AMOUNT_MISMATCH),
    unmatched: toNumber(summary?.UNMATCHED),
    archived: toNumber(summary?.ARCHIVED),
  }
}

export async function getMatchedInvoices(
  page?: number | string,
  pageSize = DEFAULT_PAGE_SIZE,
  supplierName?: string,
  yearMonth?: string
) {
  return getInvoicePage({
    page,
    pageSize,
    supplierName,
    yearMonth,
    where: `
      and mr.id is not null
      and nvl(mr.manual_confirm_flag, 'N') <> 'Y'
      and abs(nvl(mr.diff_amount, 0)) = 0`,
    yearMonthField: "payment",
    orderBy: "match_create_time desc nulls last, issue_date desc",
  })
}

export async function getConfirmedMatchedInvoices(
  page?: number | string,
  pageSize = DEFAULT_PAGE_SIZE,
  supplierName?: string,
  yearMonth?: string
) {
  return getInvoicePage({
    page,
    pageSize,
    supplierName,
    yearMonth,
    where: `
      and mr.id is not null
      and mr.manual_confirm_flag = 'Y'
      and abs(nvl(mr.diff_amount, 0)) = 0`,
    yearMonthField: "payment",
    orderBy: "match_create_time desc nulls last, issue_date desc",
  })
}

export async function getUnmatchedInvoices(
  page?: number | string,
  pageSize = DEFAULT_PAGE_SIZE,
  supplierName?: string,
  yearMonth?: string
) {
  return getInvoicePage({
    page,
    pageSize,
    supplierName,
    yearMonth,
    where: `
      and not exists (
        select 1
        from ETLKP.INVOICE_MATCH_RECORD_ZJB existed_mr
        where existed_mr.header_id = to_char(ih.id)
          and nvl(existed_mr.is_deleted, '0') <> '1'
      )`,
  })
}

export async function getAmountMismatchInvoices(
  page?: number | string,
  pageSize = DEFAULT_PAGE_SIZE,
  supplierName?: string,
  yearMonth?: string
) {
  return getInvoicePage({
    page,
    pageSize,
    supplierName,
    yearMonth,
    where: `
      and mr.id is not null
      and abs(nvl(mr.diff_amount, 0)) > 0`,
    orderBy: "abs(nvl(diff_amount, 0)) desc, issue_date desc",
  })
}

export async function getManualAssociationInvoices(
  page?: number | string,
  pageSize = DEFAULT_PAGE_SIZE,
  supplierName?: string,
  yearMonth?: string
) {
  noStore()
  const requestedPage = normalizePage(page)
  const currentPageSize = pageSize
  const supplier = normalizeSearch(supplierName)
  const ym = normalizeYearMonth(yearMonth)
  const dateWhere = ym
    ? ` and to_char(ih.issue_date, 'yyyy-mm') = :yearMonth`
    : ""
  const activeStore = await getActiveStore()
  const unmatchedStoreWhere = invoiceNameStoreWhere(activeStore)
  const mismatchStoreWhere = invoiceStoreWhere(activeStore, "pb")
  const invoiceSearchWhere = supplier
    ? ` and (
          ih.seller_name like '%' || :supplierName || '%'
          or ih.buyer_name like '%' || :supplierName || '%'
          or ih.invoice_no like '%' || :supplierName || '%'
        )`
    : ""
  const mismatchSearchWhere = supplier
    ? ` and (
          ih.seller_name like '%' || :supplierName || '%'
          or ih.buyer_name like '%' || :supplierName || '%'
          or ih.invoice_no like '%' || :supplierName || '%'
          or latest_mr.target_no like '%' || :supplierName || '%'
          or pb.sphbillno like '%' || :supplierName || '%'
        )`
    : ""
  const manualFromSql = `
    from (
      select
        to_char(ih.id) id,
        ih.invoice_no,
        ih.invoice_type_name,
        ih.is_red_invoice,
        ih.issue_date,
        ih.seller_name,
        ih.buyer_name,
        ih.seller_tax_no,
        ih.buyer_tax_no,
        ih.amount_excl_tax,
        ih.tax_amount,
        ih.amount_incl_tax,
        ih.source_system,
        null match_id,
        null target_object_type,
        null target_no,
        null match_status,
        null match_score,
        null manual_confirm_flag,
        null diff_amount,
        null match_create_time,
        null sphbillno,
        null oa_sphbillno,
        null manual_doc_no,
        null supplier_name,
        null payment_amount,
        null business_type,
        null payment_create_time,
        null remark
      from ETLKP.INVOICE_HEADER ih
      where nvl(ih.is_deleted, '0') <> '1'
        and not exists (
          select 1
          from ETLKP.INVOICE_MATCH_RECORD_ZJB existed_mr
          where existed_mr.header_id = to_char(ih.id)
            and nvl(existed_mr.is_deleted, '0') <> '1'
        )
        and not exists (
          select 1
          from ETLKP.PAYMENT_STORE_NAME psn
          where (
            trim(psn.tax_no) = trim(ih.seller_tax_no)
            or (
              ih.seller_tax_no is null
              and trim(psn.store_name) = trim(ih.seller_name)
            )
          )
        )
        ${invoiceSearchWhere}
        ${dateWhere}
        ${unmatchedStoreWhere}
      union all
      select
        to_char(ih.id) id,
        ih.invoice_no,
        ih.invoice_type_name,
        ih.is_red_invoice,
        ih.issue_date,
        ih.seller_name,
        ih.buyer_name,
        ih.seller_tax_no,
        ih.buyer_tax_no,
        ih.amount_excl_tax,
        ih.tax_amount,
        ih.amount_incl_tax,
        ih.source_system,
        latest_mr.id match_id,
        latest_mr.target_object_type,
        latest_mr.target_no,
        latest_mr.match_status,
        latest_mr.match_score,
        latest_mr.manual_confirm_flag,
        latest_mr.diff_amount,
        latest_mr.create_time match_create_time,
        pb.sphbillno,
        null oa_sphbillno,
        null manual_doc_no,
        pb.supplier_name,
        pb.payment_amount,
        pb.business_type,
        pb.create_time payment_create_time,
        latest_mr.remark
      from ETLKP.INVOICE_HEADER ih
      join (
        select *
        from (
          select mr.*,
                 row_number() over (
                   partition by mr.header_id
                   order by mr.update_time desc nulls last, mr.create_time desc nulls last
                 ) rn
          from ETLKP.INVOICE_MATCH_RECORD_ZJB mr
          where nvl(mr.is_deleted, '0') <> '1'
        )
        where rn = 1
      ) latest_mr on latest_mr.header_id = to_char(ih.id)
      left join ETLKP.PAYMENT_BILL pb
        on pb.id = latest_mr.target_object_id
       and nvl(pb.is_deleted, '0') <> '1'
      where nvl(ih.is_deleted, '0') <> '1'
        and abs(nvl(latest_mr.diff_amount, 0)) > 0
        and not exists (
          select 1
          from ETLKP.PAYMENT_STORE_NAME psn
          where (
            trim(psn.tax_no) = trim(ih.seller_tax_no)
            or (
              ih.seller_tax_no is null
              and trim(psn.store_name) = trim(ih.seller_name)
            )
          )
        )
        ${mismatchSearchWhere}
        ${dateWhere}
        ${mismatchStoreWhere}
    )
  `
  const countBinds = {
    ...(supplier ? { supplierName: supplier } : {}),
    ...(ym ? { yearMonth: ym } : {}),
    ...storeBinds(activeStore, true),
  }
  const totalRows = await executeOracle<CountRow>(
    `select count(*) total ${manualFromSql}`,
    countBinds
  )
  const total = toNumber(totalRows[0]?.TOTAL)
  const totalPages = Math.max(1, Math.ceil(total / currentPageSize))
  const currentPage = Math.min(requestedPage, totalPages)
  const offset = (currentPage - 1) * currentPageSize
  const binds: Record<string, string | number> = {
    offset,
    endRow: offset + currentPageSize,
  }
  if (supplier) binds.supplierName = supplier
  if (ym) binds.yearMonth = ym
  Object.assign(binds, storeBinds(activeStore, true))
  const rows = await executeOracle<InvoiceRow>(
    `select *
     from (
       select data_rows.*, row_number() over (order by issue_date desc, id desc) rn
       ${manualFromSql} data_rows
     )
     where rn > :offset and rn <= :endRow
     order by rn`,
    binds
  )

  return pageResult(rows.map(mapInvoice), total, currentPage, currentPageSize)
}

/** OA 鍒楄〃銆屽崟鎹被鍨嬨€嶇瓫閫夐」涓?ETLKP.OA_BILL.TYPE_01 甯歌鍙栧€煎榻愩€?*/
const OA_DOC_TYPE_FILTER_SYNONYMS: Record<string, string[]> = {
  expense: ["缁煎悎璐圭敤", "涓氬姟鎷涘緟", "鍔炲叕鐢ㄥ搧", "璐圭敤鎶ラ攢", "expense"],
  payment: ["鍙戠エ鍏ヨ处", "浠樻鐢宠", "payment"],
  project: ["项目无合同", "项目有合同", "project"],
  maintenance: ["缁翠繚缁翠慨", "maintenance"],
  hr: ["浜轰簨涓撶敤", "hr"],
  asset: ["鍥哄畾璧勪骇", "asset"],
}

/**
 * OA 鍗曟嵁鍒嗛〉銆傝〃锛欵TLKP.OA_BILL
 * 榛樿鍒楁寜褰撳墠 ETLKP.OA_BILL 缁撴瀯锛? * 鍗曟嵁鍙?SPHBILLNO锛岄棬搴?STORE_ID/PAYMENT_STORE_NAME锛岀被鍨?TYPE_01锛岀敵璇蜂汉 LASTNAME锛屼緵搴斿晢 SUPPLIER_NAME锛岄儴闂?DEPARTMENTNAME锛岄噾棰?PAYMENT_AMOUNT锛屼笟鍔℃棩鏈?CREATE_TIME銆? * 鑻ュ叾浠栫幆澧冭〃缁撴瀯涓嶅悓锛屽彲鐢?OA_BILL_*_EXPR 瑕嗙洊銆? * 鍙戠エ鍏宠仈锛欼NVOICE_MATCH_RECORD_ZJB锛堥粯璁?target_object_type = 鎶ラ攢锛屽彲鐢?OA_BILL_TARGET_OBJECT_TYPE 瑕嗙洊锛夈€? */
export async function getOaBills(
  page?: number | string | string[],
  pageSize = DEFAULT_PAGE_SIZE,
  keyword?: string | string[],
  docType?: string | string[],
  yearMonth?: string | string[]
): Promise<PageResult<OaBillItem>> {
  noStore()
  const oaDocTypeExpr =
    process.env.OA_BILL_DOC_TYPE_EXPR?.trim() || "ob.type_01"
  const oaDocNoExpr =
    process.env.OA_BILL_DOC_NO_EXPR?.trim() || "ob.sphbillno"
  const oaStoreExpr =
    process.env.OA_BILL_STORE_EXPR?.trim() || "ob.store_id"
  const oaAmountExpr = process.env.OA_BILL_AMOUNT_EXPR?.trim() || "ob.payment_amount"
  const oaDateExpr =
    process.env.OA_BILL_BUSINESS_DATE_EXPR?.trim() || "ob.create_time"
  const oaDeptExpr =
    process.env.OA_BILL_DEPT_EXPR?.trim() || "ob.departmentname"
  const oaApplicantExpr =
    process.env.OA_BILL_APPLICANT_EXPR?.trim() || "ob.lastname"
  const oaSupplierExpr =
    process.env.OA_BILL_SUPPLIER_EXPR?.trim() || "ob.supplier_name"
  const requestedPage = normalizePage(page)
  const size = pageSize ?? DEFAULT_PAGE_SIZE
  const kw = normalizeSearch(keyword)
  const ym = normalizeYearMonth(yearMonth)
  const docTypeKey = firstQueryString(docType)?.trim()
  const docTypeSynonyms =
    docTypeKey && docTypeKey !== "all"
      ? OA_DOC_TYPE_FILTER_SYNONYMS[docTypeKey] ?? [docTypeKey]
      : []

  const keywordWhere = kw
    ? ` and (
          (${oaDocNoExpr}) like '%' || :oaKeyword || '%'
          or (${oaApplicantExpr}) like '%' || :oaKeyword || '%'
          or (${oaSupplierExpr}) like '%' || :oaKeyword || '%'
          or (${oaDeptExpr}) like '%' || :oaKeyword || '%'
        )`
    : ""
  const docTypePlaceholders = docTypeSynonyms.map((_, i) => `:oaDt${i}`).join(", ")
  const docTypeWhere = docTypeSynonyms.length
    ? ` and trim(${oaDocTypeExpr}) in (${docTypePlaceholders})`
    : ""
  const monthWhere = ym
    ? ` and to_char((${oaDateExpr}), 'yyyy-mm') = :yearMonth`
    : ""

  const filterBinds: Record<string, string> = {}
  if (kw) filterBinds.oaKeyword = kw
  docTypeSynonyms.forEach((v, i) => {
    filterBinds[`oaDt${i}`] = v
  })
  if (ym) filterBinds.yearMonth = ym

  const totalRows = await executeOracle<CountRow>(
    `select count(*) total
     from ETLKP.OA_BILL ob
     where nvl(ob.is_deleted, '0') <> '1'
     ${keywordWhere}
     ${docTypeWhere}
     ${monthWhere}`,
    filterBinds
  )
  const total = toNumber(totalRows[0]?.TOTAL)
  const totalPages = Math.max(1, Math.ceil(total / size))
  const currentPage = Math.min(requestedPage, totalPages)
  const offset = (currentPage - 1) * size

  type OaRow = {
    ID: string
    DOC_TYPE: string | null
    DOC_NO: string | null
    STORE_ID: string | null
    STORE_NAME: string | null
    APPLICANT_NAME: string | null
    SUPPLIER_NAME: string | null
    DEPT_NAME: string | null
    BUSINESS_DATE: Date | string | null
    AMOUNT: number | null
    LINKED_INVOICES: number
    MATCHED_AMOUNT: number | null
    LINKED_BANK_TXN: number
    MATCH_STATUS: string | null
    MANUAL_CONFIRM_FLAG: string | null
    EXCEPTION_FLAG: string | null
  }

  const binds: Record<string, string | number> = {
    offset,
    endRow: offset + size,
    ...filterBinds,
  }

  const rows = await executeOracle<OaRow>(
    `select *
     from (
       select data_rows.*,
              row_number() over (
                order by business_date desc nulls last, doc_no desc nulls last
              ) rn
       from (
         select to_char(ob.id) id,
                ${oaDocTypeExpr} doc_type,
                ${oaDocNoExpr} doc_no,
                ${oaStoreExpr} store_id,
                psn.store_name,
                ${oaApplicantExpr} applicant_name,
                ${oaSupplierExpr} supplier_name,
                ${oaDeptExpr} dept_name,
                ${oaDateExpr} business_date,
                ${oaAmountExpr} amount,
                count(ih.id) linked_invoices,
                ${matchedInvoiceAmountSql} matched_amount,
                0 linked_bank_txn,
                max(mr.match_status) match_status,
                max(mr.manual_confirm_flag) manual_confirm_flag,
                max(mr.exception_flag) exception_flag
         from ETLKP.OA_BILL ob
         left join ETLKP.INVOICE_MATCH_RECORD_ZJB mr
           on trim(mr.target_object_id) = trim(to_char(ob.id))
          and nvl(mr.is_deleted, '0') <> '1'
         left join ETLKP.INVOICE_HEADER ih
           on to_char(ih.id) = mr.header_id
          and nvl(ih.is_deleted, '0') <> '1'
         left join ETLKP.PAYMENT_STORE_NAME psn
           on trim(psn.store_id) = trim(${oaStoreExpr})
         where nvl(ob.is_deleted, '0') <> '1'
         ${keywordWhere}
         ${docTypeWhere}
         ${monthWhere}
         group by to_char(ob.id),
                  ${oaDocTypeExpr},
                  ${oaDocNoExpr},
                  ${oaStoreExpr},
                  psn.store_name,
                  ${oaApplicantExpr},
                  ${oaSupplierExpr},
                  ${oaDeptExpr},
                  ${oaDateExpr},
                  ${oaAmountExpr}
       ) data_rows
     )
     where rn > :offset and rn <= :endRow
     order by rn`,
    binds
  )

  const items = rows.map<OaBillItem>((row) => {
    const linkedInvoices = toNumber(row.LINKED_INVOICES)
    const amount = toNumber(row.AMOUNT)
    const matchStatus = row.MATCH_STATUS?.trim()
    const isConfirmed =
      row.MANUAL_CONFIRM_FLAG === "Y" ||
      matchStatus === "OA确认" ||
      matchStatus === "CONFIRMED"
    const isException = row.EXCEPTION_FLAG === "Y"

    return {
      id: row.ID,
      docType: row.DOC_TYPE || "-",
      docNo: row.DOC_NO || "-",
      storeId: row.STORE_ID || "-",
      storeName: row.STORE_NAME || row.STORE_ID || "-",
      applicant: row.APPLICANT_NAME || "-",
      supplierName: row.SUPPLIER_NAME || "-",
      department: row.DEPT_NAME || "-",
      businessDate: formatDate(row.BUSINESS_DATE),
      amount,
      linkedInvoices,
      linkedTransactions: toNumber(row.LINKED_BANK_TXN),
      status:
        linkedInvoices <= 0
          ? "pending"
          : isConfirmed && !isException
            ? "completed"
            : "partial",
      linkedInvoiceItems: [],
    }
  })

  return pageResult(items, total, currentPage, size)
}

export async function getOaBillLinkedInvoices(
  oaBillId: string
): Promise<OaLinkedInvoiceItem[]> {
  noStore()
  const id = oaBillId.trim()
  if (!id) return []

  type OaInvoiceRow = {
    TARGET_OBJECT_ID: string
    ID: string | number
    INVOICE_NO: string | null
    SELLER_NAME: string | null
    BUYER_NAME: string | null
    ISSUE_DATE: Date | string | null
    AMOUNT_INCL_TAX: number | null
    IS_RED_INVOICE: string | null
    MATCH_STATUS: string | null
    MATCH_SCORE: number | null
    DIFF_AMOUNT: number | null
    MANUAL_CONFIRM_FLAG: string | null
  }

  const invoiceRows = await executeOracle<OaInvoiceRow>(
    `select mr.target_object_id,
            ih.id,
            ih.invoice_no,
            ih.seller_name,
            ih.buyer_name,
            ih.issue_date,
            ih.amount_incl_tax,
            ih.is_red_invoice,
            mr.match_status,
            mr.match_score,
            mr.diff_amount,
            mr.manual_confirm_flag
     from ETLKP.INVOICE_MATCH_RECORD_ZJB mr
     join ETLKP.INVOICE_HEADER ih
       on to_char(ih.id) = mr.header_id
      and nvl(ih.is_deleted, '0') <> '1'
     where nvl(mr.is_deleted, '0') <> '1'
       and trim(mr.target_object_id) = trim(:oaBillId)
     order by ih.issue_date desc nulls last, ih.invoice_no`,
    { oaBillId: id }
  )

  return invoiceRows.map((invoice) => ({
    id: String(invoice.ID),
    invoiceNo: invoice.INVOICE_NO || "-",
    sellerName: invoice.SELLER_NAME || "-",
    buyerName: invoice.BUYER_NAME || "-",
    invoiceDate: formatDate(invoice.ISSUE_DATE),
    amount: invoiceAmount(
      {
        ID: invoice.ID,
        INVOICE_NO: invoice.INVOICE_NO || "",
        INVOICE_TYPE_NAME: null,
        IS_RED_INVOICE: invoice.IS_RED_INVOICE,
        ISSUE_DATE: invoice.ISSUE_DATE || "",
        SELLER_NAME: invoice.SELLER_NAME,
        BUYER_NAME: invoice.BUYER_NAME,
        SELLER_TAX_NO: null,
        BUYER_TAX_NO: null,
        AMOUNT_EXCL_TAX: null,
        TAX_AMOUNT: null,
        AMOUNT_INCL_TAX: invoice.AMOUNT_INCL_TAX,
        SOURCE_SYSTEM: null,
        MATCH_ID: null,
        TARGET_OBJECT_TYPE: null,
        TARGET_NO: null,
        MATCH_STATUS: invoice.MATCH_STATUS,
        MATCH_SCORE: invoice.MATCH_SCORE,
        MANUAL_CONFIRM_FLAG: invoice.MANUAL_CONFIRM_FLAG,
        DIFF_AMOUNT: invoice.DIFF_AMOUNT,
        SPHBILLNO: null,
        OA_SPHBILLNO: null,
        MANUAL_DOC_NO: null,
        SUPPLIER_NAME: null,
        PAYMENT_AMOUNT: null,
        BUSINESS_TYPE: null,
        PAYMENT_CREATE_TIME: null,
        REMARK: null,
      },
      invoice.AMOUNT_INCL_TAX
    ),
    matchStatus: invoice.MATCH_STATUS || "-",
    matchScore: Math.round(toNumber(invoice.MATCH_SCORE)),
    diffAmount: toNumber(invoice.DIFF_AMOUNT),
    manualConfirmed: invoice.MANUAL_CONFIRM_FLAG === "Y",
  }))
}

export async function getPaymentBills(
  page?: number | string,
  pageSize = DEFAULT_PAGE_SIZE,
  supplierName?: string,
  status?: string,
  yearMonth?: string
) {
  noStore()
  const currentPage = normalizePage(page)
  const offset = (currentPage - 1) * pageSize
  const supplier = normalizeSearch(supplierName)
  const ym = normalizeYearMonth(yearMonth)
  const activeStore = await getActiveStore()
  const storeWhere = paymentBillStoreWhere(activeStore)
  const supplierWhere = supplier
    ? ` and (
          pb.supplier_name like '%' || :supplierName || '%'
          or pb.sphbillno like '%' || :supplierName || '%'
        )`
    : ""
  const monthWhere = ym
    ? ` and to_char(pb.create_time, 'yyyy-mm') = :yearMonth`
    : ""
  type Row = {
    ID: string
    SPHBILLNO: string
    SUPPLIER_NAME: string | null
    STORE_ID: string | null
    STORE_NAME: string | null
    STORE_TAX_NO: string | null
    PAYMENT_AMOUNT: number | null
    BUSINESS_TYPE: string | null
    CREATE_TIME: Date | string
    LINKED_INVOICES: number
    MATCHED_AMOUNT: number | null
  }

  const statusHaving =
    status === "completed"
      ? `having count(ih.id) > 0 and pb.payment_amount - ${matchedInvoiceAmountSql} <= 0`
      : status === "partial"
        ? `having count(ih.id) > 0 and pb.payment_amount - ${matchedInvoiceAmountSql} > 0`
        : status === "pending"
          ? "having count(ih.id) = 0"
          : ""
  const totalRows = await executeOracle<CountRow>(
    `select count(*) total
     from (
       select pb.id
       from ETLKP.PAYMENT_BILL pb
       left join ETLKP.INVOICE_MATCH_RECORD_ZJB mr
         on mr.target_object_id = pb.id
        and nvl(mr.is_deleted, '0') <> '1'
       left join ETLKP.INVOICE_HEADER ih
         on to_char(ih.id) = mr.header_id
        and nvl(ih.is_deleted, '0') <> '1'
       left join ETLKP.PAYMENT_STORE_NAME psn
         on psn.store_id = pb.store_id
       where nvl(pb.is_deleted, '0') <> '1'
       ${supplierWhere}
       ${monthWhere}
       ${storeWhere}
       group by pb.id, pb.payment_amount
       ${statusHaving}
     )`,
    {
      ...(supplier ? { supplierName: supplier } : {}),
      ...(ym ? { yearMonth: ym } : {}),
      ...storeBinds(activeStore),
    }
  )
  const binds: Record<string, string | number> = {
    offset,
    endRow: offset + pageSize,
  }
  if (supplier) binds.supplierName = supplier
  if (ym) binds.yearMonth = ym
  Object.assign(binds, storeBinds(activeStore))
  const rows = await executeOracle<Row>(
    `select *
     from (
       select data_rows.*, row_number() over (order by create_time desc, sphbillno desc) rn
       from (
         select pb.id,
                pb.sphbillno,
                pb.supplier_name,
                pb.store_id,
                psn.store_name,
                psn.tax_no store_tax_no,
                pb.payment_amount,
                pb.business_type,
                pb.create_time,
                count(ih.id) linked_invoices,
                ${matchedInvoiceAmountSql} matched_amount
         from ETLKP.PAYMENT_BILL pb
         left join ETLKP.INVOICE_MATCH_RECORD_ZJB mr
           on mr.target_object_id = pb.id
          and nvl(mr.is_deleted, '0') <> '1'
         left join ETLKP.INVOICE_HEADER ih
           on to_char(ih.id) = mr.header_id
          and nvl(ih.is_deleted, '0') <> '1'
         left join ETLKP.PAYMENT_STORE_NAME psn
           on psn.store_id = pb.store_id
         where nvl(pb.is_deleted, '0') <> '1'
         ${supplierWhere}
         ${monthWhere}
         ${storeWhere}
         group by pb.id, pb.sphbillno, pb.supplier_name, pb.store_id, psn.store_name, psn.tax_no, pb.payment_amount, pb.business_type, pb.create_time
         ${statusHaving}
       ) data_rows
     )
     where rn > :offset and rn <= :endRow
     order by rn`,
    binds
  )

  const items = rows.map<PaymentBillItem>((row) => {
    const linkedInvoices = toNumber(row.LINKED_INVOICES)
    const amount = toNumber(row.PAYMENT_AMOUNT)
    const matchedAmount = toNumber(row.MATCHED_AMOUNT)
    const remainingAmount = Math.max(0, amount - matchedAmount)

    return {
      id: row.ID,
      source: "浠樻绯荤粺",
      docType: row.BUSINESS_TYPE ? `付款单(${row.BUSINESS_TYPE})` : "付款单",
      docNo: row.SPHBILLNO,
      partner: row.SUPPLIER_NAME || "-",
      storeId: row.STORE_ID || "-",
      storeName: row.STORE_NAME || "-",
      storeTaxNo: row.STORE_TAX_NO?.trim() || undefined,
      businessDate: formatDate(row.CREATE_TIME),
      amount,
      matchedAmount,
      remainingAmount,
      linkedInvoices,
      linkedTransactions: 0,
      status:
        linkedInvoices > 0 && remainingAmount > 0
          ? "partial"
          : linkedInvoices > 0
            ? "completed"
            : "pending",
    }
  })

  return pageResult(items, toNumber(totalRows[0]?.TOTAL), currentPage, pageSize)
}

export async function getPaymentBillSummary(
  supplierName?: string,
  yearMonth?: string,
  status?: string
): Promise<PaymentBillSummary> {
  noStore()
  const supplier = normalizeSearch(supplierName)
  const ym = normalizeYearMonth(yearMonth)
  const activeStore = await getActiveStore()
  const storeWhere = paymentBillStoreWhere(activeStore)
  const supplierWhere = supplier
    ? ` and (
          pb.supplier_name like '%' || :supplierName || '%'
          or pb.sphbillno like '%' || :supplierName || '%'
        )`
    : ""
  const monthWhere = ym
    ? ` and to_char(pb.create_time, 'yyyy-mm') = :yearMonth`
    : ""
  const statusHaving =
    status === "completed"
      ? `having count(ih.id) > 0 and pb.payment_amount - ${matchedInvoiceAmountSql} <= 0`
      : status === "partial"
        ? `having count(ih.id) > 0 and pb.payment_amount - ${matchedInvoiceAmountSql} > 0`
        : status === "pending"
          ? "having count(ih.id) = 0"
          : ""
  const rows = await executeOracle<PaymentBillSummaryRow>(
    `select
       count(*) total,
       sum(case when linked_invoices > 0 and payment_amount - matched_amount <= 0 then 1 else 0 end) completed,
       sum(case when linked_invoices > 0 and payment_amount - matched_amount > 0 then 1 else 0 end) partial,
       sum(case when linked_invoices = 0 then 1 else 0 end) pending,
       sum(payment_amount) total_amount,
       sum(linked_invoices) linked_invoices
     from (
       select pb.id,
              nvl(pb.payment_amount, 0) payment_amount,
              count(ih.id) linked_invoices,
              ${matchedInvoiceAmountSql} matched_amount
       from ETLKP.PAYMENT_BILL pb
       left join ETLKP.INVOICE_MATCH_RECORD_ZJB mr
         on mr.target_object_id = pb.id
        and nvl(mr.is_deleted, '0') <> '1'
       left join ETLKP.INVOICE_HEADER ih
         on to_char(ih.id) = mr.header_id
        and nvl(ih.is_deleted, '0') <> '1'
       left join ETLKP.PAYMENT_STORE_NAME psn
         on psn.store_id = pb.store_id
       where nvl(pb.is_deleted, '0') <> '1'
       ${supplierWhere}
       ${monthWhere}
       ${storeWhere}
       group by pb.id, pb.payment_amount
       ${statusHaving}
      )`,
    {
      ...(supplier ? { supplierName: supplier } : {}),
      ...(ym ? { yearMonth: ym } : {}),
      ...storeBinds(activeStore),
    }
  )
  const summary = rows[0]

  return {
    total: toNumber(summary?.TOTAL),
    completed: toNumber(summary?.COMPLETED),
    partial: toNumber(summary?.PARTIAL),
    pending: toNumber(summary?.PENDING),
    totalAmount: toNumber(summary?.TOTAL_AMOUNT),
    linkedInvoices: toNumber(summary?.LINKED_INVOICES),
  }
}

export async function getPaymentStoreNames() {
  const stores = await getPaymentStores()
  return stores.map((store) => store.name)
}

async function getDashboardMonthlySummary(year: number): Promise<DashboardData["monthlySummary"]> {
  const yearText = String(year)
  const activeStore = await getActiveStore()
  const invoiceStoreFilter = invoiceStoreWhere(activeStore)
  const paymentStoreFilter = paymentBillStoreWhere(activeStore)
  const months = Array.from({ length: 12 }, (_, index) => ({
    month: `${index + 1}月`,
    matchedPending: 0,
    amountMismatch: 0,
    unmatched: 0,
    confirmed: 0,
    paymentBills: 0,
  }))

  const [invoiceRows, paymentRows] = await Promise.all([
    executeOracle<DashboardMonthlyInvoiceRow>(
      `select to_char(coalesce(payment_create_time, issue_date), 'mm') month_no,
              sum(case when match_id is not null and abs(nvl(diff_amount, 0)) = 0 and nvl(manual_confirm_flag, 'N') <> 'Y' then 1 else 0 end) matched,
              sum(case when match_id is not null and abs(nvl(diff_amount, 0)) > 0 then 1 else 0 end) amount_mismatch,
              sum(case when match_id is null then 1 else 0 end) unmatched,
              sum(case when match_id is not null and abs(nvl(diff_amount, 0)) = 0 and manual_confirm_flag = 'Y' then 1 else 0 end) archived
       ${invoiceFromSql}
       and to_char(coalesce(pb.create_time, ob.create_time, mb.business_date, mr.create_time, ih.issue_date), 'yyyy') = :dashboardYear
       ${invoiceStoreFilter}
       )
       group by to_char(coalesce(payment_create_time, issue_date), 'mm')`,
      {
        dashboardYear: yearText,
        ...storeBinds(activeStore, true),
      }
    ),
    executeOracle<DashboardMonthlyPaymentRow>(
      `select to_char(pb.create_time, 'mm') month_no,
              count(*) total
       from ETLKP.PAYMENT_BILL pb
       left join ETLKP.PAYMENT_STORE_NAME psn
         on psn.store_id = pb.store_id
       where nvl(pb.is_deleted, '0') <> '1'
         and to_char(pb.create_time, 'yyyy') = :dashboardYear
         ${paymentStoreFilter}
       group by to_char(pb.create_time, 'mm')`,
      {
        dashboardYear: yearText,
        ...storeBinds(activeStore),
      }
    ),
  ])

  for (const row of invoiceRows) {
    const index = Number(row.MONTH_NO) - 1
    if (index < 0 || index >= months.length) continue
    months[index].matchedPending = toNumber(row.MATCHED)
    months[index].amountMismatch = toNumber(row.AMOUNT_MISMATCH)
    months[index].unmatched = toNumber(row.UNMATCHED)
    months[index].confirmed = toNumber(row.ARCHIVED)
  }

  for (const row of paymentRows) {
    const index = Number(row.MONTH_NO) - 1
    if (index < 0 || index >= months.length) continue
    months[index].paymentBills = toNumber(row.TOTAL)
  }

  return months
}

export async function getDashboardData(yearMonth?: string): Promise<DashboardData> {
  noStore()
  const dashboardYear = new Date().getFullYear()
  const [invoiceSummary, paymentBillSummary, recent, monthlySummary] =
    await Promise.all([
      getInvoiceSummary(undefined, yearMonth),
      getPaymentBillSummary(undefined, yearMonth),
      getMatchedInvoices(1, 5, undefined, yearMonth),
      getDashboardMonthlySummary(dashboardYear),
    ])

  return {
    stats: {
      matchedPending: invoiceSummary.matched,
      amountMismatch: invoiceSummary.amountMismatch,
      unmatched: invoiceSummary.unmatched,
      confirmed: invoiceSummary.archived,
      paymentBills: paymentBillSummary.total,
    },
    recentActivities: recent.items.map((item) => ({
      id: item.id,
      type: "invoice",
      action: "发票匹配成功",
      detail: `发票号 ${item.invoiceNo} 已匹配至单据 ${item.matchedDoc}`,
      time: item.matchedDocDate,
      status: "success",
    })),
    monthlySummary,
  }
}

