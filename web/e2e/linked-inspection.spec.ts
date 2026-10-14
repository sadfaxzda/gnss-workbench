import { test, expect } from '@playwright/test'

test('epoch and satellite selection stay linked, and invalid epochs clear the position', async ({
  page,
}, testInfo) => {
  await page.goto('/')
  await page.getByLabel('回放速度').selectOption('0')
  await page.getByRole('button', { name: '开始运行', exact: true }).click()
  await expect(page.getByText('600 / 600 历元')).toBeVisible()
  await page.getByRole('button', { name: /^跳转到历元 120–179/ }).click()
  await expect(page.getByText('查看历元 120', { exact: true })).toBeVisible()
  const inspector = page.getByRole('region', { name: '选中卫星详情' })
  await expect(inspector.getByRole('heading', { name: 'G19' })).toBeVisible()
  await expect(inspector).toContainText('已剔除')
  await page.getByRole('button', { name: '下一个历元', exact: true }).click()
  await expect(page.getByText('查看历元 121', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '逐星诊断', exact: true }).click()
  await page.getByRole('button', { name: '查看卫星 G20', exact: true }).click()
  await expect(inspector.getByRole('heading', { name: 'G20' })).toBeVisible()
  await expect(page.getByRole('button', { name: '选择卫星 G20', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await page.getByRole('button', { name: '选择卫星 G19', exact: true }).press('Enter')
  await expect(page.getByRole('button', { name: '查看卫星 G19', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await page.getByRole('button', { name: /^跳转到历元 520–529/ }).click()
  await expect(inspector).toContainText('本历元无该卫星观测')
  await expect(page.getByText('本历元无逐星诊断数据')).toBeVisible()
  await page.getByRole('button', { name: '实时定位', exact: true }).click()
  const latitude = page
    .locator('.position-details > div')
    .filter({ has: page.getByText('纬度', { exact: true }) })
  await expect(latitude).toContainText('—')
  await page.getByRole('button', { name: /^跳转到历元 460–479/ }).click()
  await expect(page.getByText('可用卫星 3 颗 · 最低要求 4 颗', { exact: true })).toBeVisible()
  await expect(latitude).toContainText('—')
  await expect(page.getByText('三维解差', { exact: true })).toBeVisible()
  await expect(page.getByText(/不足四颗卫星，无法独立解算/)).toHaveCount(0)
  await expect(page.getByText(/修正距离为两种解/)).toHaveCount(0)
  await page.getByRole('button', { name: /^跳转到历元 520–529/ }).click()
  // The clock plot is a second entry to the same timeline, including empty plot space.
  const clock = page.getByRole('img', { name: '接收机钟差随历元变化' })
  const box = (await clock.boundingBox())!
  await clock.click({ position: { x: box.width * 0.5, y: box.height * 0.5 } })
  await expect(page.getByText('查看历元 520', { exact: true })).not.toBeVisible()
  await expect(latitude).not.toContainText('—')
  await page.getByRole('button', { name: '回到最新', exact: true }).click()
  await expect(page.getByText('跟随最新历元', { exact: true })).toBeVisible()
  for (const viewport of [
    { width: 1280, height: 720 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport)
    // ECharts resizes its canvas through ResizeObserver after the viewport changes.
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(viewport.width)
    await page.screenshot({
      path: testInfo.outputPath(`workbench-${viewport.width}.png`),
      fullPage: true,
    })
  }
})
