import type { EChartsOption } from 'echarts'

// Canvas and SVG share the semantic colors documented in DESIGN.md.
export const chartColors = {
  baseline: '#b86e1b',
  improved: '#087e8b',
  excluded: '#b86e1b',
  rejected: '#b03f36',
  clock: '#426da6',
  grid: '#e5ecf1',
  text: '#536879',
  muted: '#a3b5c2',
} as const

export const chartBase: EChartsOption = {
  animation: false,
  color: [chartColors.baseline, chartColors.improved],
  textStyle: {
    fontFamily: '-apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif',
    color: chartColors.text,
    fontSize: 12,
  },
  tooltip: { trigger: 'axis', confine: true },
  grid: { left: 58, right: 28, top: 30, bottom: 45 },
}
