// /style 의 3D 지도 견본을 극각(도)별로 찍는다. 개발 서버에서만 동작한다(window.__mapControls).
// 사용: node scripts/shot-map.mjs <url> <출력 접두사> <대기ms> <극각,...> [방위각,...]
import { chromium } from "playwright"

const [url, prefix, waitMs = "5000", polars = "10,50,78", azimuths = ""] = process.argv.slice(2)
const browser = await chromium.launch({
  channel: "chrome",
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"],
})
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
page.on("console", (m) => m.type() === "error" && console.log("[console]", m.text()))
await page.goto(url, { waitUntil: "load" })
const box = async () => {
  const el = page.locator("#map canvas").first()
  await el.scrollIntoViewIfNeeded()
  return page.evaluate(() => {
    const r = document.querySelector("#map canvas").parentElement.parentElement.parentElement.getBoundingClientRect()
    return { x: r.x, y: r.y, width: r.width, height: r.height }
  })
}
await box()
await page.waitForTimeout(Number(waitMs))
await page.screenshot({ path: `${prefix}-initial.png`, clip: await box() })
const az = azimuths ? azimuths.split(",").map(Number) : []
for (const [i, deg] of polars.split(",").map(Number).entries()) {
  await page.evaluate(
    async ([p, a]) => {
      const c = window.__mapControls
      if (a !== undefined) await c.rotateAzimuthTo((a * Math.PI) / 180, true)
      await c.rotatePolarTo((p * Math.PI) / 180, true)
    },
    [deg, az[i]]
  )
  await page.waitForTimeout(1600)
  await page.screenshot({ path: `${prefix}-${deg}.png`, clip: await box() })
}
await browser.close()
