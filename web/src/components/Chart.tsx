import { useEffect, useRef } from 'react'
import * as echarts from 'echarts/core'
import { LineChart, BarChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

echarts.use([
  LineChart,
  BarChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer,
])

export function Chart({
  option,
  height = 310,
  label,
}: {
  option: EChartsOption
  height?: number
  label: string
}) {
  const container = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)
  useEffect(() => {
    if (!container.current) return
    chart.current = echarts.init(container.current, undefined, { renderer: 'canvas' })
    const observer = new ResizeObserver(() => chart.current?.resize())
    observer.observe(container.current)
    return () => {
      observer.disconnect()
      chart.current?.dispose()
      chart.current = null
    }
  }, [])
  useEffect(() => {
    chart.current?.setOption(option, { notMerge: true, lazyUpdate: true })
  }, [option])
  return <div ref={container} role="img" aria-label={label} style={{ height, width: '100%' }} />
}
