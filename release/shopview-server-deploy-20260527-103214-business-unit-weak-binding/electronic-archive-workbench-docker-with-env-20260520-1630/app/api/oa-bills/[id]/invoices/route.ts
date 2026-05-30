import { NextResponse } from "next/server"
import { getOaBillLinkedInvoices } from "@/lib/etl-data"

export const dynamic = "force-dynamic"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const invoices = await getOaBillLinkedInvoices(decodeURIComponent(id))

  return NextResponse.json({ invoices })
}
