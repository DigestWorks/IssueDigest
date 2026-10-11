// 페이지의 한 요소만 스크린샷. 사용: node scripts/shot-element.mjs <url> <selector> <out.png> [대기ms] [배율]
import { chromium } from "playwright"
const [url, selector, out, waitMs = "3000", scale = "2"] = process.argv.slice(2)
const b = await chromium.launch({ channel: "chrome" })
const p = await b.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: Number(scale) })
const logs = []
p.on("pageerror", (e) => logs.push(e.message))
p.on("console", (m) => m.type() === "error" && logs.push(m.text()))
// /style 은 지도 견본을 넣은 뒤 networkidle 에 도달하지 않아 30초 제한에 걸린다(원인 미확인). load 후 대기한다
await p.goto(url, { waitUntil: "load" })
await p.locator(selector).scrollIntoViewIfNeeded()
await p.waitForTimeout(Number(waitMs))
await p.locator(selector).screenshot({ path: out })
console.log(logs.join("\n") || "no errors")
await b.close()
