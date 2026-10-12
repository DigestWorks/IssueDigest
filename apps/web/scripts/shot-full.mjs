// 페이지 전체 스크린샷. 사용: node scripts/shot-full.mjs <url> <out.png>
import { chromium } from "playwright"
const [url, out] = process.argv.slice(2)
const b = await chromium.launch({ channel: "chrome" })
const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
const logs = []
p.on("console", (m) => m.type() === "error" && logs.push(m.text()))
p.on("pageerror", (e) => logs.push(e.message))
await p.goto(url, { waitUntil: "load" })
await p.waitForTimeout(2500)
await p.screenshot({ path: out, fullPage: true })
console.log(logs.join("\n") || "no errors", await p.evaluate(() => document.body.scrollHeight))
await b.close()
