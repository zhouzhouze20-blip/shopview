import { NextRequest, NextResponse } from "next/server"
import {
  createAuthSession,
  ensureAdminUser,
  findUserByUsername,
  userCanAccessStore,
  verifyUserPassword,
} from "@/lib/auth"

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as {
      username?: string
      password?: string
      storeId?: string
      storeName?: string
    }
    const username = body.username?.trim()
    const password = body.password ?? ""
    const storeId = body.storeId?.trim()
    const storeName = body.storeName?.trim()

    if (!username || !password) {
      return NextResponse.json(
        { error: "请输入用户名和密码" },
        { status: 400 }
      )
    }

    let userId: string | undefined
    if (username.toLowerCase() === "admin") {
      const adminPassword = process.env.ADMIN_PASSWORD || "admin"
      if (password !== adminPassword) {
        return NextResponse.json({ error: "管理员密码错误" }, { status: 401 })
      }
      userId = await ensureAdminUser()
    } else {
      userId = await findUserByUsername(username)
      if (userId) {
        const passwordValid = await verifyUserPassword(userId, password)
        if (!passwordValid) {
          return NextResponse.json(
            { error: "用户名或密码错误" },
            { status: 401 }
          )
        }
        if (storeId && storeName) {
          const canAccessStore = await userCanAccessStore(userId, storeId, storeName)
          if (!canAccessStore) {
            return NextResponse.json(
              { error: "当前用户没有所选门店的数据范围权限" },
              { status: 403 }
            )
          }
        }
      }
    }

    if (!userId) {
      return NextResponse.json(
        { error: "用户不存在或已停用" },
        { status: 401 }
      )
    }

    await createAuthSession(userId)
    return NextResponse.json({ ok: true })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
