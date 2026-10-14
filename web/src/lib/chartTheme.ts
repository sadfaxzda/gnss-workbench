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
  baseline: '#707b84',
  improved: '#355f79',
  excluded: '#a3463e',
  rejected: '#a3463e',
  clock: '#626c75',
  satellite: '#626c75',
  residual: '#626c75',
  grid: '#e2e5e8',
  text: '#535d66',
  muted: '#626c75',
  plotBaseline: '#707b84',
  plotImproved: '#355f79',
  plotSelected: '#355f79',
  plotText: '#535d66',
  plotGrid: '#e2e5e8',
  plotAxis: '#7a858e',
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
