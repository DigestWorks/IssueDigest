// 페이지를 연 뒤 정해진 시각(ms)마다 화면을 찍는다(등장 애니메이션 확인용).
// 사용: node scripts/shot-sequence.mjs <url> <출력 접두사> <시각,...> [폭] [높이]
import { chromium } from "playwright"

const [url, prefix, times = "300,800,1300,2000,3000", width = "1440", height = "900"] = process.argv.slice(2)
const browser = await chromium.launch({
  channel: "chrome",
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"],
})
const page = await browser.newPage({ viewport: { width: Number(width), height: Number(height) } })
const errors = []
page.on("pageerror", (e) => errors.push(String(e)))
page.on("console", (m) => m.type() === "error" && errors.push(m.text()))
await page.goto(url, { waitUntil: "load" })
await page.locator("canvas").first().waitFor()
const start = Date.now()
for (const t of times.split(",").map(Number)) {
  const wait = t - (Date.now() - start)
  if (wait > 0) await page.waitForTimeout(wait)
  await page.screenshot({ path: `${prefix}-${t}.png` })
}
console.log(errors.length ? errors.join("\n") : "no errors")
await browser.close()
