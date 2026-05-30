import "server-only"

import { createHmac, timingSafeEqual } from "crypto"

const WECOM_QR_CONNECT_URL = "https://open.work.weixin.qq.com/wwopen/sso/qrConnect"
const WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"
const WECOM_STATE_TTL_SECONDS = 10 * 60

function requiredEnv(name: string) {
  const value = process.env[name]
  if (!value) throw new Error(`Missing environment variable: ${name}`)
  return value
}

function optionalEnv(...names: string[]) {
  for (const name of names) {
    const value = process.env[name]?.trim()
    if (value) return value
  }
  return ""
}

function base64UrlEncode(value: string) {
  return Buffer.from(value, "utf8").toString("base64url")
}

function base64UrlDecode(value: string) {
  return Buffer.from(value, "base64url").toString("utf8")
}

function getStateSecret() {
  return optionalEnv("AUTH_SECRET", "NEXTAUTH_SECRET", "WECOM_STATE_SECRET") || getWecomAppSecret()
}

function safeNextPath(nextPath: string | null | undefined) {
  const value = (nextPath || "/").trim()
  if (!value.startsWith("/") || value.startsWith("//")) return "/"
  return value
}

function signStatePayload(payload: string) {
  return createHmac("sha256", getStateSecret()).update(payload).digest("base64url")
}

export function createWecomState(nextPath = "/") {
  const payload = base64UrlEncode(
    JSON.stringify({
      typ: "wecom_login",
      next: safeNextPath(nextPath),
      exp: Math.floor(Date.now() / 1000) + WECOM_STATE_TTL_SECONDS,
    })
  )
  return `${payload}.${signStatePayload(payload)}`
}

export function decodeWecomState(state: string | null | undefined) {
  if (!state) throw new Error("企业微信登录状态缺失")

  const [payload, signature] = state.split(".")
  if (!payload || !signature) throw new Error("企业微信登录状态无效")

  const expectedSignature = signStatePayload(payload)
  const expected = Buffer.from(expectedSignature)
  const actual = Buffer.from(signature)
  if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) {
    throw new Error("企业微信登录状态无效")
  }

  const data = JSON.parse(base64UrlDecode(payload)) as {
    typ?: string
    next?: string
    exp?: number
  }
  if (data.typ !== "wecom_login") throw new Error("企业微信登录状态无效")
  if (!data.exp || data.exp < Math.floor(Date.now() / 1000)) {
    throw new Error("企业微信登录状态已失效")
  }

  return {
    next: safeNextPath(data.next),
  }
}

function getWecomAppSecret() {
  return optionalEnv("WECOM_APP_SECRET", "WECOM_CORP_SECRET") || requiredEnv("WECOM_CORP_SECRET")
}

function getWecomRedirectBaseUrl() {
  return optionalEnv("WECOM_REDIRECT_BASE_URL", "APP_URL", "NEXT_PUBLIC_APP_URL").replace(/\/+$/, "")
}

function getWecomCallbackUrl() {
  const configuredCallback = optionalEnv("WECOM_REDIRECT_URI")
  if (configuredCallback) return configuredCallback

  const baseUrl = getWecomRedirectBaseUrl()
  if (!baseUrl) throw new Error("Missing environment variable: WECOM_REDIRECT_BASE_URL or APP_URL")
  return `${baseUrl}/api/auth/wecom/callback`
}

export function getWecomAuthorizeUrl(nextPath = "/") {
  const enabled = optionalEnv("WECOM_ENABLED").toLowerCase()
  if (["0", "false", "no", "off"].includes(enabled)) {
    throw new Error("企业微信登录未启用")
  }

  const corpId = requiredEnv("WECOM_CORP_ID")
  const agentId = requiredEnv("WECOM_AGENT_ID")
  const redirectUri = getWecomCallbackUrl()
  const state = createWecomState(nextPath)
  const params = new URLSearchParams({
    appid: corpId,
    agentid: agentId,
    redirect_uri: redirectUri,
    state,
    lang: "zh",
  })
  return `${WECOM_QR_CONNECT_URL}?${params.toString()}`
}

export async function getWecomAccessToken(secretOverride?: string) {
  const corpId = requiredEnv("WECOM_CORP_ID")
  const secret = secretOverride ?? getWecomAppSecret()
  const response = await fetch(
    `${WECOM_API_BASE}/gettoken?corpid=${encodeURIComponent(corpId)}&corpsecret=${encodeURIComponent(secret)}`,
    { cache: "no-store" }
  )
  const data = (await response.json()) as {
    errcode?: number
    errmsg?: string
    access_token?: string
  }
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`WeCom gettoken failed: ${data.errmsg ?? data.errcode}`)
  }
  if (!data.access_token) throw new Error("WeCom access_token is empty")
  return data.access_token
}

export async function getWecomUserIdByCode(code: string) {
  const accessToken = await getWecomAccessToken()
  const response = await fetch(
    `${WECOM_API_BASE}/auth/getuserinfo?access_token=${encodeURIComponent(accessToken)}&code=${encodeURIComponent(code)}`,
    { cache: "no-store" }
  )
  const data = (await response.json()) as {
    errcode?: number
    errmsg?: string
    UserId?: string
    userid?: string
  }
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`WeCom getuserinfo failed: ${data.errmsg ?? data.errcode}`)
  }
  const userId = data.UserId ?? data.userid
  if (!userId) throw new Error("WeCom userid is empty")
  return userId
}

export type WecomUser = {
  userid: string
  name: string
  mobile?: string
  email?: string
  departmentName?: string
}

type WecomJson = {
  errcode?: number
  errmsg?: string
}

async function fetchWecomJson<T extends WecomJson>(url: string, label: string) {
  const response = await fetch(url, { cache: "no-store" })
  const data = (await response.json()) as T
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`WeCom ${label} failed: ${data.errmsg ?? data.errcode}`)
  }
  return data
}

async function getDepartmentMap(accessToken: string) {
  const data = await fetchWecomJson<{
    errcode?: number
    errmsg?: string
    department?: { id: number; name: string }[]
  }>(
    `https://qyapi.weixin.qq.com/cgi-bin/department/list?access_token=${encodeURIComponent(accessToken)}`,
    "department/list"
  )
  return new Map((data.department ?? []).map((dept) => [dept.id, dept.name]))
}

async function getUserDetail(
  accessToken: string,
  userid: string,
  departmentMap: Map<number, string>
): Promise<WecomUser | undefined> {
  const data = await fetchWecomJson<{
    errcode?: number
    errmsg?: string
    userid?: string
    name?: string
    mobile?: string
    email?: string
    department?: number[]
  }>(
    `https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token=${encodeURIComponent(accessToken)}&userid=${encodeURIComponent(userid)}`,
    "user/get"
  )
  const resolvedUserId = data.userid ?? userid
  if (!resolvedUserId) return undefined

  return {
    userid: resolvedUserId,
    name: data.name || resolvedUserId,
    mobile: data.mobile,
    email: data.email,
    departmentName:
      data.department
        ?.map((departmentId) => departmentMap.get(departmentId))
        .filter((name): name is string => Boolean(name))
        .join(", ") || undefined,
  }
}

async function getDepartmentUsers(accessToken: string, departmentId: number) {
  const data = await fetchWecomJson<{
    errcode?: number
    errmsg?: string
    userlist?: {
      userid: string
      name?: string
      mobile?: string
      email?: string
      department?: number[]
    }[]
  }>(
    `https://qyapi.weixin.qq.com/cgi-bin/user/list?access_token=${encodeURIComponent(accessToken)}&department_id=${departmentId}&fetch_child=1`,
    `user/list department ${departmentId}`
  )
  return data.userlist ?? []
}

async function getTagUsers(accessToken: string, tagId: number) {
  const data = await fetchWecomJson<{
    errcode?: number
    errmsg?: string
    userlist?: { userid: string; name?: string }[]
  }>(
    `https://qyapi.weixin.qq.com/cgi-bin/tag/get?access_token=${encodeURIComponent(accessToken)}&tagid=${tagId}`,
    `tag/get ${tagId}`
  )
  return data.userlist ?? []
}

export async function getWecomUsers(): Promise<WecomUser[]> {
  const accessToken = await getWecomAccessToken()
  const agentId = requiredEnv("WECOM_AGENT_ID")
  const [departmentMap, agentData] = await Promise.all([
    getDepartmentMap(accessToken),
    fetchWecomJson<{
      errcode?: number
      errmsg?: string
      allow_userinfos?: { user?: { userid: string }[] }
      allow_partys?: { partyid?: number[] }
      allow_tags?: { tagid?: number[] }
    }>(
      `https://qyapi.weixin.qq.com/cgi-bin/agent/get?access_token=${encodeURIComponent(accessToken)}&agentid=${encodeURIComponent(agentId)}`,
      "agent/get"
    ),
  ])

  const users = new Map<string, WecomUser>()
  const addUser = (user: WecomUser | undefined) => {
    if (user?.userid) users.set(user.userid, user)
  }

  for (const user of agentData.allow_userinfos?.user ?? []) {
    addUser(await getUserDetail(accessToken, user.userid, departmentMap))
  }

  for (const departmentId of agentData.allow_partys?.partyid ?? []) {
    const departmentUsers = await getDepartmentUsers(accessToken, departmentId)
    for (const user of departmentUsers) {
      users.set(user.userid, {
        userid: user.userid,
        name: user.name || user.userid,
        mobile: user.mobile,
        email: user.email,
        departmentName:
          user.department
            ?.map((id) => departmentMap.get(id))
            .filter((name): name is string => Boolean(name))
            .join(", ") || undefined,
      })
    }
  }

  for (const tagId of agentData.allow_tags?.tagid ?? []) {
    const tagUsers = await getTagUsers(accessToken, tagId)
    for (const user of tagUsers) {
      if (!users.has(user.userid)) {
        addUser(await getUserDetail(accessToken, user.userid, departmentMap))
      }
    }
  }

  return Array.from(users.values())
}

export async function getWecomContactUsers(): Promise<WecomUser[]> {
  const accessToken = await getWecomAccessToken(requiredEnv("WECOM_CONTACT_SECRET"))
  const departmentMap = await getDepartmentMap(accessToken)
  const response = await fetch(
    `https://qyapi.weixin.qq.com/cgi-bin/user/list?access_token=${encodeURIComponent(accessToken)}&department_id=1&fetch_child=1`,
    { cache: "no-store" }
  )
  const data = (await response.json()) as {
    errcode?: number
    errmsg?: string
    userlist?: {
      userid: string
      name?: string
      mobile?: string
      email?: string
      department?: number[]
    }[]
  }
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`WeCom user/list failed: ${data.errmsg ?? data.errcode}`)
  }

  return (data.userlist ?? [])
    .filter((user) => user.userid)
    .map((user) => ({
      userid: user.userid,
      name: user.name || user.userid,
      mobile: user.mobile,
      email: user.email,
      departmentName:
        user.department
          ?.map((departmentId) => departmentMap.get(departmentId))
          .filter((name): name is string => Boolean(name))
          .join(", ") || undefined,
    }))
}
