import { NextResponse } from "next/server"
import { getWecomAuthorizeUrl } from "@/lib/wecom"

export async function GET(request: Request) {
  try {
    const url = new URL(request.url)
    const nextPath = url.searchParams.get("next") || "/"
    return NextResponse.json({ url: getWecomAuthorizeUrl(nextPath) })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "企微登录配置错误" },
      { status: 500 }
    )
  }
}
