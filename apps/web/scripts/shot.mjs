// 스테이지 화면 확인용 스크린샷. 설치된 Chrome 을 GPU 가속 headless 로 띄운다.
// 사용: node scripts/shot.mjs <url> <out.png> [질문] [대기ms] [폭] [높이]
import { chromium } from "playwright"

const [url, out, question, waitMs = "9000", w = "1600", h = "960"] = process.argv.slice(2)
const browser = await chromium.launch({
  channel: "chrome",
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"],
})
const page = await browser.newPage({ viewport: { width: Number(w), height: Number(h) } })
const logs = []
page.on("console", (m) => (m.type() === "error" || m.type() === "warning") && logs.push(`[${m.type()}] ${m.text()}`))
page.on("pageerror", (e) => logs.push(`[pageerror] ${e.message}`))
await page.goto(url, { waitUntil: "networkidle" })
await page.waitForTimeout(2500)
if (question) {
  await page.getByPlaceholder("이슈에 대해 질문하세요").fill(question)
  await page.keyboard.press("Enter")
}
await page.waitForTimeout(Number(waitMs))
await page.screenshot({ path: out })
console.log(logs.filter((l) => !l.includes("THREE.Clock") && !l.includes("PCFSoftShadowMap")).join("\n") || "no errors")
await browser.close()
