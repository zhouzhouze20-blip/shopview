import { NextRequest, NextResponse } from "next/server"
import { createAuthSession, findUserByWecomUserId } from "@/lib/auth"
import { decodeWecomState, getWecomUserIdByCode } from "@/lib/wecom"

function publicUrl(path: string) {
  const appUrl = process.env.APP_URL || process.env.NEXT_PUBLIC_APP_URL
  if (appUrl) return new URL(path, appUrl)
  return undefined
}

function redirectUrl(path: string, requestUrl: string) {
  return publicUrl(path) ?? new URL(path, requestUrl)
}

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code")
  const state = request.nextUrl.searchParams.get("state")
  if (!code || !state) {
    return NextResponse.redirect(redirectUrl("/login?error=missing_code", request.url))
  }

  try {
    const statePayload = decodeWecomState(state)
    const wecomUserId = await getWecomUserIdByCode(code)
    const userId = await findUserByWecomUserId(wecomUserId)
    if (!userId) {
      return NextResponse.redirect(
        redirectUrl(
          `/login?error=unbound_wecom&userid=${encodeURIComponent(wecomUserId)}`,
          request.url
        )
      )
    }
    await createAuthSession(userId)
    return NextResponse.redirect(redirectUrl(statePayload.next, request.url))
  } catch (error) {
    const message = error instanceof Error ? error.message : "wecom_error"
    return NextResponse.redirect(
      redirectUrl(`/login?error=${encodeURIComponent(message)}`, request.url)
    )
  }
}
