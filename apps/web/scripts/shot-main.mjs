// 메인 화면에 질문을 보내고 정해진 시각(ms)마다 화면을 찍는다.
// 사용: node scripts/shot-main.mjs <url> <출력 접두사> <질문> <시각,...>
import { chromium } from "playwright"

const [url, prefix, question, times = "1500,4000,9000"] = process.argv.slice(2)
const browser = await chromium.launch({
  channel: "chrome",
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"],
})
const page = await browser.newPage({ viewport: { width: 1600, height: 960 } })
const errors = []
page.on("pageerror", (e) => errors.push(String(e)))
page.on("console", (m) => m.type() === "error" && errors.push(m.text()))
await page.goto(url, { waitUntil: "load" })
await page.waitForTimeout(1500)
await page.screenshot({ path: `${prefix}-0.png` })
await page.getByLabel("질문 입력").fill(question)
await page.keyboard.press("Enter")
const start = Date.now()
for (const t of times.split(",").map(Number)) {
  const wait = t - (Date.now() - start)
  if (wait > 0) await page.waitForTimeout(wait)
  await page.screenshot({ path: `${prefix}-${t}.png` })
}
console.log(errors.length ? errors.join("\n") : "no errors")
await browser.close()
