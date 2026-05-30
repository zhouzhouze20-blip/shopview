import { NextRequest, NextResponse } from "next/server"
import { getManualAssociationInvoices } from "@/lib/etl-data"

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const supplierName = searchParams.get("supplierName") ?? undefined
  const pageSize = Math.min(Number(searchParams.get("pageSize") ?? 5000), 5000)

  const invoicePage = await getManualAssociationInvoices(
    1,
    Number.isFinite(pageSize) && pageSize > 0 ? pageSize : 5000,
    supplierName
  )

  return NextResponse.json({
    invoices: invoicePage.items,
    total: invoicePage.total,
  })
}
