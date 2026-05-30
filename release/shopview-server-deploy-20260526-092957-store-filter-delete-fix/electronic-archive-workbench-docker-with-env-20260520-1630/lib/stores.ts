import "server-only"

import { unstable_noStore as noStore } from "next/cache"
import { cookies } from "next/headers"
import { executeOracle } from "@/lib/oracle"

export const ACTIVE_STORE_ID_COOKIE = "activeStoreId"
export const ACTIVE_STORE_NAME_COOKIE = "activeStoreName"
export const ACTIVE_STORE_TAX_NO_COOKIE = "activeStoreTaxNo"

type StoreRow = {
  STORE_ID: string | null
  STORE_NAME: string | null
  TAX_NO: string | null
}

export type StoreOption = {
  id: string
  name: string
  taxNo?: string
}

export async function getPaymentStores(): Promise<StoreOption[]> {
  noStore()
  const rows = await executeOracle<StoreRow>(
    `select min(trim(store_id)) store_id,
            trim(store_name) store_name,
            max(trim(tax_no)) tax_no
     from ETLKP.PAYMENT_STORE_NAME
     where store_name is not null
     group by trim(store_name)
     order by trim(store_name)`
  )

  return rows
    .map((row) => ({
      id: row.STORE_ID?.trim() || row.STORE_NAME?.trim() || "",
      name: row.STORE_NAME?.trim() || "",
      taxNo: row.TAX_NO?.trim() || undefined,
    }))
    .filter((store) => store.id && store.name)
}

export async function getActiveStore(): Promise<StoreOption | undefined> {
  const cookieStore = await cookies()
  const id = cookieStore.get(ACTIVE_STORE_ID_COOKIE)?.value?.trim()
  const encodedName = cookieStore.get(ACTIVE_STORE_NAME_COOKIE)?.value?.trim()
  const encodedTaxNo = cookieStore.get(ACTIVE_STORE_TAX_NO_COOKIE)?.value?.trim()
  const name = encodedName ? decodeURIComponent(encodedName) : undefined
  const taxNoFromCookie = encodedTaxNo ? decodeURIComponent(encodedTaxNo).trim() : undefined

  if (!id || !name) return undefined

  if (taxNoFromCookie) return { id, name, taxNo: taxNoFromCookie }

  const rows = await executeOracle<Pick<StoreRow, "TAX_NO">>(
    `select max(trim(tax_no)) tax_no
     from ETLKP.PAYMENT_STORE_NAME
     where trim(store_id) = :storeId
        or trim(store_name) = :storeName`,
    { storeId: id, storeName: name }
  )

  return { id, name, taxNo: rows[0]?.TAX_NO?.trim() || undefined }
}
