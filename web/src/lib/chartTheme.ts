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
  baseline: '#98763b',
  improved: '#365f71',
  excluded: '#98763b',
  rejected: '#a33f34',
  clock: '#60758b',
  grid: '#e0e4dc',
  text: '#505951',
  muted: '#636b63',
  plotBaseline: '#d3b66b',
  plotImproved: '#8bb7ca',
  plotSelected: '#ead17a',
  plotText: '#cbd5c8',
  plotGrid: '#47534a',
  plotAxis: '#82917f',
} as const

export const chartBase: EChartsOption = {
  animation: false,
  color: [chartColors.baseline, chartColors.improved],
  textStyle: {
    color: chartColors.text,
    fontSize: 12,
  },
  tooltip: { trigger: 'axis', confine: true },
  grid: { left: 58, right: 28, top: 30, bottom: 45 },
}
