import { getConfirmedMatchedInvoices } from "@/lib/etl-data"

export const dynamic = "force-dynamic"

const EXPORT_PAGE_SIZE = 50000

function csvCell(value: string | number | null | undefined) {
  const text = value === null || value === undefined ? "" : String(value)
  return `"${text.replace(/"/g, '""')}"`
}

function csvExcelTextCell(value: string | number | null | undefined) {
  const text = value === null || value === undefined ? "" : String(value)
  const formula = `="${text.replace(/"/g, '""')}"`
  return csvCell(formula)
}

function csvRow(values: (string | number | null | undefined)[]) {
  return values.map(csvCell).join(",")
}

function filenameDate() {
  return new Date().toISOString().slice(0, 10).replace(/-/g, "")
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const supplierName = searchParams.get("supplierName") ?? undefined
  const yearMonth = searchParams.get("yearMonth") ?? undefined
  const invoicePage = await getConfirmedMatchedInvoices(
    1,
    EXPORT_PAGE_SIZE,
    supplierName,
    yearMonth
  )

  const rows = [
    csvRow([
      "发票号码",
      "销方名称",
      "购方名称",
      "开票日期",
      "业务单据日期",
      "不含税金额",
      "税额",
      "价税合计",
      "匹配单据",
      "单据来源",
      "来源系统",
      "确认状态",
    ]),
    ...invoicePage.items.map((invoice) =>
      [
        csvExcelTextCell(invoice.invoiceNo),
        csvCell(invoice.sellerName),
        csvCell(invoice.buyerName),
        csvCell(invoice.invoiceDate),
        csvCell(invoice.matchedDocDate),
        csvCell(invoice.amount),
        csvCell(invoice.taxAmount),
        csvCell(invoice.totalAmount),
        csvExcelTextCell(invoice.matchedDoc),
        csvCell(invoice.documentSource),
        csvCell(invoice.source),
        csvCell("已确认"),
      ].join(",")
    ),
  ]

  return new Response(`\uFEFF${rows.join("\r\n")}`, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="confirmed-report-${filenameDate()}.csv"`,
      "Cache-Control": "no-store",
    },
  })
}
