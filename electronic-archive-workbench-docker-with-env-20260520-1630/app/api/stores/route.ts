import { NextResponse } from "next/server"
import { getPaymentStores } from "@/lib/stores"

export const dynamic = "force-dynamic"

export async function GET() {
  try {
    const stores = await getPaymentStores()
    return NextResponse.json({ stores })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return NextResponse.json({ stores: [], error: message }, { status: 200 })
  }
}
