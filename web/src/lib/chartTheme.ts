import type { EChartsOption } from 'echarts'

// Equal metres per pixel keeps a GNSS trajectory geometrically faithful on resize.
export function equalAxisBounds(points: number[][], width: number, height: number) {
  if (!points.length || width <= 0 || height <= 0) return null
  const x = points.map((point) => point[0])
  const y = points.map((point) => point[1])
  const xMin = Math.min(...x),
    xMax = Math.max(...x)
  const yMin = Math.min(...y),
    yMax = Math.max(...y)
  const scale =
    Math.max((xMax - xMin) / width, (yMax - yMin) / height, 1 / Math.min(width, height)) * 1.12
  return {
    xMin: (xMin + xMax - scale * width) / 2,
    xMax: (xMin + xMax + scale * width) / 2,
    yMin: (yMin + yMax - scale * height) / 2,
    yMax: (yMin + yMax + scale * height) / 2,
  }
}

// Canvas and SVG share the semantic colors documented in DESIGN.md.
export const chartColors = {
  baseline: '#b86e1b',
  improved: '#087882',
  excluded: '#b86e1b',
  rejected: '#b43e38',
  clock: '#426da6',
  grid: '#e8edef',
  text: '#52636e',
  muted: '#a3afb7',
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
