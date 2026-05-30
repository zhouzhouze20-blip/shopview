import { cpSync, existsSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const args = process.argv.slice(2)

for (let index = 0; index < args.length; index += 1) {
  const arg = args[index]

  if ((arg === "-p" || arg === "--port") && args[index + 1]) {
    process.env.PORT = args[index + 1]
    index += 1
    continue
  }

  if (arg.startsWith("--port=")) {
    process.env.PORT = arg.slice("--port=".length)
  }
}

const projectRoot = dirname(dirname(fileURLToPath(import.meta.url)))
const standaloneRoot = join(projectRoot, ".next", "standalone")
const staticSource = join(projectRoot, ".next", "static")
const staticTarget = join(standaloneRoot, ".next", "static")
const publicSource = join(projectRoot, "public")
const publicTarget = join(standaloneRoot, "public")

if (existsSync(staticSource) && !existsSync(staticTarget)) {
  mkdirSync(dirname(staticTarget), { recursive: true })
  cpSync(staticSource, staticTarget, { recursive: true })
}

if (existsSync(publicSource) && !existsSync(publicTarget)) {
  cpSync(publicSource, publicTarget, { recursive: true })
}

await import("../.next/standalone/server.js")
