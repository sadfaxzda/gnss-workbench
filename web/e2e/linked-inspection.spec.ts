import { test, expect } from '@playwright/test'

test('epoch and satellite selection stay linked, and invalid epochs clear the position', async ({
  page,
}) => {
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
  await expect(inspector).toContainText('当前历元没有这颗卫星的诊断数据')
  await expect(page.getByText('当前历元没有可显示的逐星诊断。')).toBeVisible()
  await page.getByRole('button', { name: '实时定位', exact: true }).click()
  const latitude = page
    .locator('.position-details > div')
    .filter({ has: page.getByText('纬度', { exact: true }) })
  await expect(latitude).toContainText('—')
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
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      viewport.width,
    )
  }
})
