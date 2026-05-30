#!/usr/bin/env node
/**
 * `next build` with `output: "standalone"` removes `.next/standalone` first.
 * On Windows, EBUSY happens if `pnpm start` (standalone server) or another process
 * still holds files under that directory. This script tries early removal with retries.
 */
import { access, rm } from "node:fs/promises"
import { constants } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..")
const standalone = path.join(root, ".next", "standalone")

async function exists(p) {
  try {
    await access(p, constants.F_OK)
    return true
  } catch {
    return false
  }
}

async function main() {
  if (!(await exists(standalone))) {
    return
  }

  const waitMs = [400, 700, 1000, 1500, 2000, 2500, 3000]

  for (let i = 0; i < waitMs.length; i++) {
    try {
      await rm(standalone, { recursive: true, force: true })
      console.log("[prebuild] Removed .next/standalone")
      return
    } catch (err) {
      const code = err?.code
      const retryable = code === "EBUSY" || code === "EPERM" || code === "EACCES"
      if (retryable && i < waitMs.length - 1) {
        console.warn(
          `[prebuild] ${code} on .next/standalone — retry ${i + 2}/${waitMs.length} after ${waitMs[i]}ms…`
        )
        await new Promise((r) => setTimeout(r, waitMs[i]))
        continue
      }
      console.error(
        "[prebuild] Cannot remove .next/standalone. Stop `pnpm start` / any Node server using this project, close File Explorer inside `.next\\standalone`, then run `pnpm build` again."
      )
      console.error(err?.message ?? err)
      process.exit(1)
    }
  }
}

await main()
