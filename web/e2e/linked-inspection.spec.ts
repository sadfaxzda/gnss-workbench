import { test, expect, type Locator } from '@playwright/test'

async function expectCanvasSize(plot: Locator) {
  await expect
    .poll(() =>
      plot.evaluate((element) => {
        const canvas = element.querySelector('canvas')
        return (
          !!canvas &&
          Math.abs(parseFloat(canvas.style.width) - element.clientWidth) < 1 &&
          Math.abs(parseFloat(canvas.style.height) - element.clientHeight) < 1
        )
      }),
    )
    .toBe(true)
}

test('epoch and satellite selection stay linked, and invalid epochs clear the position', async ({
  page,
  context,
  browserName,
}, testInfo) => {
  if (browserName === 'chromium')
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])
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
  // The engineering grid keeps numeric sorting, column sizing and selection functional.
  const grid = page.getByRole('table', { name: '卫星观测表' })
  await page.getByRole('button', { name: '按残差 / m排序', exact: true }).click()
  const residualValues = (await grid.locator('tbody tr td:nth-child(5)').allTextContents()).map(
    Number,
  )
  expect(residualValues).toEqual([...residualValues].sort((a, b) => a - b))
  const resizer = page.getByRole('separator', { name: '调整残差 / m列宽', exact: true })
  await resizer.press('ArrowRight')
  await expect(resizer).toHaveAttribute('aria-valuenow', '142')
  await resizer.press('Home')
  await expect(resizer).toHaveAttribute('aria-valuenow', '126')
  await page.getByLabel('卫星观测筛选').selectOption('excluded')
  await expect(grid.locator('tbody tr')).toHaveCount(1)
  await expect(grid.locator('tbody')).toContainText('G19')
  await expect(page.getByText('显示 1 / 8 条', { exact: true })).toBeVisible()
  await page.getByLabel('卫星观测筛选').selectOption('all')
  await page.getByRole('button', { name: '按卫星排序', exact: true }).click()
  await page.getByRole('button', { name: '查看卫星 G19', exact: true }).press('ArrowDown')
  await expect(inspector.getByRole('heading', { name: 'G20' })).toBeVisible()
  await page.getByRole('button', { name: '查看卫星 G19', exact: true }).click()
  await expect(page.getByRole('table', { name: '全局检验结果' })).toBeVisible()
  const baselineTest = page
    .getByRole('table', { name: '全局检验结果' })
    .getByRole('row')
    .filter({ hasText: '普通解' })
  await expect(baselineTest).toContainText('未通过')
  await page.getByRole('button', { name: '复制选中行', exact: true }).click()
  await expect(page.getByText('已复制 G19', { exact: true })).toBeVisible()

  await expect(page.getByRole('contentinfo', { name: '应用状态栏' })).toContainText(
    '600 / 600 历元',
  )
  await expect(page.getByLabel('解算进度')).toHaveCount(0)
  await page.screenshot({ path: testInfo.outputPath('desktop-diagnostics.png'), fullPage: true })
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.getByRole('button', { name: '选择卫星 G28', exact: true }).click()
  const selectedRow = (await grid
    .getByRole('button', { name: '查看卫星 G28', exact: true })
    .boundingBox())!
  const gridViewport = (await page.locator('.grid-scroll').boundingBox())!
  expect(selectedRow.y + selectedRow.height).toBeLessThanOrEqual(
    gridViewport.y + gridViewport.height + 1,
  )
  await page.setViewportSize({ width: 390, height: 844 })
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBeLessThanOrEqual(390)
  await page.screenshot({
    path: testInfo.outputPath('desktop-diagnostics-mobile.png'),
    fullPage: true,
  })
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.getByRole('button', { name: '选择卫星 G19', exact: true }).click()
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
  await page.getByText('更多解算参数', { exact: true }).click()
  await expect(page.getByText('三维解差', { exact: true })).toBeVisible()
  await page.getByText('更多解算参数', { exact: true }).click()
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
  // Shared time windows survive epoch changes and stay linked across both plots.
  const residual = page.getByRole('img', { name: '普通解与改进解的残差时间趋势' })
  await page.getByRole('button', { name: '放大残差图', exact: true }).click()
  await expect(residual).toHaveAttribute('data-zoom-span', '50.000')
  await expect(clock).toHaveAttribute('data-zoom-span', '50.000')
  const zoomedBox = (await clock.boundingBox())!
  await clock.click({ position: { x: zoomedBox.width * 0.5, y: zoomedBox.height * 0.5 } })
  const epochAfterZoom = Number(await page.getByLabel('历元时间轴').inputValue())
  expect(epochAfterZoom).toBeGreaterThanOrEqual(150)
  expect(epochAfterZoom).toBeLessThanOrEqual(450)
  await page.getByRole('button', { name: '上一个历元', exact: true }).click()
  await expect(residual).toHaveAttribute('data-zoom-span', '50.000')
  await page.getByLabel('残差趋势观测量').selectOption('G19')
  await expect(inspector.getByRole('heading', { name: 'G19' })).toBeVisible()
  await expect(residual).toHaveAttribute('data-zoom-span', '50.000')
  await page.getByRole('button', { name: '展开残差图', exact: true }).click()
  await expect(page.locator('.trajectory-panel')).not.toBeVisible()
  const expanded = (await residual.boundingBox())!
  expect(expanded.width).toBeGreaterThan(1200)
  await expectCanvasSize(residual)
  await page.screenshot({ path: testInfo.outputPath('residual-expanded.png'), fullPage: true })
  await page.getByRole('button', { name: '收起残差图', exact: true }).press('Escape')
  await expect(page.locator('.trajectory-panel')).toBeVisible()
  await page.getByRole('button', { name: '复位接收机钟差', exact: true }).click()
  await expect(residual).toHaveAttribute('data-zoom-span', '100.000')
  const trajectory = page.getByRole('img', { name: '普通解与改进解的定位轨迹' })
  await page.getByRole('button', { name: '放大定位轨迹', exact: true }).click()
  await expect(trajectory).toHaveAttribute('data-zoom-span', '50.000')
  await page.getByRole('button', { name: '下一个历元', exact: true }).click()
  await expect(trajectory).toHaveAttribute('data-zoom-span', '50.000')
  await page.getByRole('button', { name: '复位定位轨迹', exact: true }).click()
  await expect(trajectory).toHaveAttribute('data-zoom-span', '100.000')
  await page.getByRole('button', { name: '逐星对比', exact: true }).click()
  await expect(page.getByRole('img', { name: '当前历元各颗卫星的伪距残差' })).toBeVisible()
  await page.getByRole('button', { name: '时间趋势', exact: true }).click()
  await page.getByLabel('残差趋势观测量').selectOption('')
  for (const viewport of [
    { width: 1600, height: 900 },
    { width: 1280, height: 720 },
    { width: 1024, height: 768 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport)
    // ECharts resizes its canvas through ResizeObserver after the viewport changes.
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(viewport.width)
    if (viewport.width >= 1100) {
      // A wide, shallow map makes the equal-scale trajectory unreadably small.
      const trajectory = page.getByRole('img', { name: '普通解与改进解的定位轨迹' })
      const bounds = (await trajectory.boundingBox())!
      expect(bounds.height / bounds.width).toBeGreaterThanOrEqual(0.5)
    }
    const timeline = (await page.getByRole('region', { name: '统一历元回放' }).boundingBox())!
    for (const name of [
      '普通解与改进解的定位轨迹',
      '普通解与改进解的残差时间趋势',
      '接收机钟差随历元变化',
    ]) {
      const chart = (await page.getByRole('img', { name }).boundingBox())!
      expect(chart.y + chart.height).toBeLessThanOrEqual(timeline.y + 1)
    }
    for (const plot of await page.locator('.data-chart').all()) await expectCanvasSize(plot)
    await page.screenshot({
      path: testInfo.outputPath(`workbench-${viewport.width}.png`),
      fullPage: true,
    })
  }
})
