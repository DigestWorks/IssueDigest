// 시나리오를 재생한 뒤 카메라 극각을 바꿔 가며 스크린샷을 찍는다(패널 방향 확인용).
// 사용: node scripts/shot-angles.mjs <url> <출력 접두사> <질문> <대기ms> <극각(도),...>
import { chromium } from "playwright"

const [url, prefix, question, waitMs = "11000", angles = "15,45,80"] = process.argv.slice(2)
const browser = await chromium.launch({
  channel: "chrome",
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"],
})
const page = await browser.newPage({ viewport: { width: 1600, height: 960 } })
await page.goto(url, { waitUntil: "networkidle" })
await page.waitForTimeout(2500)
await page.getByPlaceholder("이슈에 대해 질문하세요").fill(question)
await page.keyboard.press("Enter")
await page.waitForTimeout(Number(waitMs))
for (const deg of angles.split(",").map(Number)) {
  await page.evaluate(async (d) => {
    const c = window.__stageControls
    await c.rotatePolarTo((d * Math.PI) / 180, true)
  }, deg)
  await page.waitForTimeout(1500)
  await page.screenshot({ path: `${prefix}-${deg}.png` })
}
await browser.close()
