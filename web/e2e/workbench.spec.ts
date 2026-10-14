import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { once } from 'node:events'

test('run actual observations, inspect evidence, reload history and export', async ({
  page,
}, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '定位与故障诊断', exact: true })).toBeAttached()
  await page.getByLabel('回放速度').selectOption('0')
  const created = page.waitForResponse(
    (response) => response.url().endsWith('/api/runs') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: '开始运行', exact: true }).click()
  const run = await (await created).json()
  await expect(page.getByText('已完成', { exact: true })).toBeVisible()
  await expect(page.getByText('600 / 600 历元')).toBeVisible()
  await page
    .getByLabel('定位状态区段')
    .selectOption({ label: '历元 120–179 · 已剔除异常卫星 · G19' })
  await expect(page.getByText('查看历元 120', { exact: true })).toBeVisible()
  await expect(page.getByText('已剔除异常卫星', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '下一区段', exact: true }).click()
  await expect(page.getByText('查看历元 180', { exact: true })).toBeVisible()
  await expect(page.getByText('定位有效', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '回到最新', exact: true }).click()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: testInfo.outputPath('workbench.png'), fullPage: true })
  await page.getByRole('button', { name: '逐星诊断', exact: true }).click()
  await expect(page.getByRole('heading', { name: '故障诊断证据' })).toBeVisible()
  await expect(page.getByRole('button', { name: '查看卫星 G19', exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByText('600 / 600 历元')).toBeVisible()
  const downloaded = page.waitForEvent('download')
  await page.getByRole('link', { name: '改进解', exact: true }).click()
  const file = await downloaded
  expect(file.suggestedFilename()).toContain('improved.csv')
  expect(await file.failure()).toBeNull()
  const csv = await readFile((await file.path())!, 'utf8')
  expect(csv.trim().split(/\r?\n/)).toHaveLength(601)
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

test('import observations, select research algorithm and inspect its evidence', async ({
  page,
}, testInfo) => {
  const lines = (await readFile('../fixtures/course/data/D02_sim_clean.jsonl', 'utf8'))
    .trim()
    .split('\n')
  const epoch = JSON.parse(lines[74])
  epoch.observations.find(
    (observation: { sat_id: string }) => observation.sat_id === 'G03',
  ).pseudorange_m += 85
  epoch.observations.find(
    (observation: { sat_id: string }) => observation.sat_id === 'G20',
  ).pseudorange_m -= 90
  await page.goto('/')
  await page.getByText('算法与自定义数据', { exact: true }).click()
  await page.getByLabel('导入观测文件').setInputFiles({
    name: '双星未知场景.jsonl',
    mimeType: 'application/json',
    buffer: Buffer.from(lines[0] + '\n' + JSON.stringify(epoch) + '\n'),
  })
  const imported = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/datasets') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: '校验并导入' }).click()
  const dataset = await (await imported).json()
  await expect(page.getByLabel('观测数据')).toHaveValue(dataset.id)
  await page.getByLabel('诊断算法').selectOption('adaptive_gnc')
  await page.getByLabel('回放速度').selectOption('0')
  await page.getByRole('button', { name: '开始运行', exact: true }).click()
  await expect(page.getByText('已完成', { exact: true })).toBeVisible()
  await expect(page.getByText('1 / 1 历元')).toBeVisible()
  await page.getByRole('button', { name: '逐星诊断', exact: true }).click()
  await expect(page.getByRole('group', { name: '卫星天空图：方位角与高度角' })).toBeVisible()
  await expect(page.getByRole('row').filter({ hasText: 'G03' }).first()).toContainText('异常剔除')
  await expect(page.getByRole('row').filter({ hasText: 'G20' }).first()).toContainText('异常剔除')
  await page.getByText(/GNC 搜索轨迹/).click()
  await expect(page.getByRole('columnheader', { name: 'MSAC / m²' })).toBeVisible()
  await expect(page.locator('.advanced-controls')).not.toHaveAttribute('open')
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: testInfo.outputPath('advanced-diagnostics.png'), fullPage: true })
  await page.setViewportSize({ width: 430, height: 932 })
  await page.getByText('算法与自定义数据', { exact: true }).click()
  const dimensions = await page.evaluate(() => ({
    viewport: innerWidth,
    content: document.documentElement.scrollWidth,
  }))
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1)
})

test('TCP pause keeps old position stale until a new epoch is received', async ({ page }) => {
  const { createServer } = await import('node:net')
  const server = createServer()
  server.listen(0, '127.0.0.1')
  await once(server, 'listening')
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('No TCP port')
  const connected = once(server, 'connection')
  let socket: import('node:net').Socket | undefined
  try {
    const lines = (await readFile('../fixtures/course/data/D02_sim_clean.jsonl', 'utf8'))
      .trim()
      .split('\n')
    await page.goto('/')
    await page.getByLabel('输入方式').selectOption('tcp')
    await page.getByLabel('TCP端口').fill(String(address.port))
    await page.getByRole('button', { name: '开始运行', exact: true }).click()
    ;[socket] = (await connected) as [import('node:net').Socket]
    socket.write(
      JSON.stringify({ type: 'meta', replay_interval_wall_s: 0.01 }) + '\n' + lines[1] + '\n',
    )
    await expect(page.getByText('定位有效', { exact: true })).toBeVisible()
    await expect(page.getByText('数据已过期 · 历史位置', { exact: true })).toBeVisible({
      timeout: 8000,
    })
    // A resumed byte stream alone does not make an old solution current again.
    socket.write('{"type":"meta","replay_interval_wall_s":0.01}\n')
    await page.reload()
    await expect(page.getByText('数据已过期 · 历史位置', { exact: true })).toBeVisible()
    socket.write(lines[2] + '\n')
    await expect(page.getByText('数据接收已恢复')).toBeVisible()
    await expect(page.getByText('定位有效', { exact: true })).toBeVisible()
    socket.end('{"type":"end","epochs_sent":2}\n')
    await expect(page.getByText('已完成', { exact: true })).toBeVisible()
    const downloaded = page.waitForEvent('download')
    await page.getByRole('link', { name: '改进解', exact: true }).click()
    const file = await downloaded
    expect((await readFile((await file.path())!, 'utf8')).trim().split(/\r?\n/)).toHaveLength(3)
  } finally {
    socket?.destroy()
    server.close()
  }
})
