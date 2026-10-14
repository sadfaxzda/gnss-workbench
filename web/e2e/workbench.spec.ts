import { test, expect } from '@playwright/test'

test('run actual observations, inspect evidence, reload history and export', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '定位与故障诊断', exact: true })).toBeVisible()
  await page.getByLabel('回放速度').selectOption('0')
  const created = page.waitForResponse(
    (response) => response.url().endsWith('/api/runs') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: '开始运行', exact: true }).click()
  const run = await (await created).json()
  await expect(page.getByText('已完成', { exact: true })).toBeVisible()
  await expect(page.getByText('600 / 600 历元')).toBeVisible()
  await page.screenshot({ path: '../docs/media/workbench.png', fullPage: true })
  await page.getByRole('button', { name: '逐星诊断', exact: true }).click()
  await expect(page.getByRole('heading', { name: '故障诊断证据' })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'G19', exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByText('600 / 600 历元')).toBeVisible()
  const downloaded = page.waitForEvent('download')
  await page.getByRole('link', { name: '改进解', exact: true }).click()
  const file = await downloaded
  expect(file.suggestedFilename()).toContain('improved.csv')
  await page.getByRole('button', { name: '实验设计', exact: true }).click()
  await expect(page.getByRole('cell', { name: '1.59 m', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '运行记录', exact: true }).click()
  await expect(page.getByRole('cell', { name: run.id.slice(0, 8), exact: true })).toBeVisible()
  expect(errors).toEqual([])
})

test('controlled fault and ablation controls work on a narrow viewport', async ({ page }) => {
  await page.setViewportSize({ width: 430, height: 932 })
  await page.goto('/')
  await page.getByRole('button', { name: '实验设计', exact: true }).click()
  await page.getByLabel('故障类型').selectOption('satellite_bias')
  await page.getByLabel('目标卫星').selectOption('G20')
  await page.getByLabel('偏差幅度', { exact: true }).fill('-95')
  await page.getByLabel('开始历元', { exact: true }).fill('43')
  await page.getByLabel('持续历元', { exact: true }).fill('27')
  await page.getByLabel('回放速度').selectOption('0')
  await page.getByRole('button', { name: '运行实验', exact: true }).click()
  await expect(page.getByText('已完成', { exact: true })).toBeVisible()
  const dimensions = await page.evaluate(() => ({
    viewport: innerWidth,
    content: document.documentElement.scrollWidth,
  }))
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1)
  await page.getByRole('button', { name: '实验设计', exact: true }).click()
  await expect(page.getByRole('row').filter({ hasText: '强故障检出率' })).toContainText('100.00')
  await page.getByRole('checkbox', { name: /启用故障检测与剔除/ }).uncheck()
  await page.getByRole('button', { name: '运行实验', exact: true }).click()
  await expect(page.getByText('已完成', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '实验设计', exact: true }).click()
  const row = page.getByRole('row').filter({ hasText: '水平误差 P95' })
  const cells = await row.getByRole('cell').allTextContents()
  expect(cells[1]).toBe(cells[2])
})
