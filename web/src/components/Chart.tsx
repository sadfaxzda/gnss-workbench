import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts/core'
import { LineChart, BarChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import { equalAxisBounds } from '../lib/chartTheme'
import { loadWorkbenchFonts } from '../lib/fonts'

echarts.use([
  LineChart,
  BarChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  CanvasRenderer,
])

export function Chart({
  option,
  height = 310,
  label,
  onPointSelect,
  onCategorySelect,
  equalScalePoints,
}: {
  option: EChartsOption
  height?: number | string
  label: string
  onPointSelect?: (index: number, series: number) => void
  onCategorySelect?: (index: number) => void
  equalScalePoints?: number[][]
}) {
  const container = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const [fontReady, setFontReady] = useState(false)
  useEffect(() => {
    let mounted = true
    void loadWorkbenchFonts().then(() => {
      if (mounted) setFontReady(true)
    })
    return () => {
      mounted = false
    }
  }, [])
  useEffect(() => {
    if (!fontReady || !container.current) return
    chart.current = echarts.init(container.current, undefined, { renderer: 'canvas' })
    const observer = new ResizeObserver(([entry]) => {
      chart.current?.resize()
      setSize({ width: entry.contentRect.width, height: entry.contentRect.height })
    })
    observer.observe(container.current)
    return () => {
      observer.disconnect()
      chart.current?.dispose()
      chart.current = null
    }
  }, [fontReady])
  useEffect(() => {
    if (!fontReady || !container.current) return
    const bounds = equalScalePoints
      ? equalAxisBounds(equalScalePoints, size.width - 86, size.height - 75)
      : null
    const scaled = bounds
      ? {
          ...option,
          xAxis: { ...option.xAxis, min: bounds.xMin, max: bounds.xMax },
          yAxis: { ...option.yAxis, min: bounds.yMin, max: bounds.yMax },
        }
      : option
    const fontFamily = getComputedStyle(container.current).fontFamily
    const tooltip = Array.isArray(scaled.tooltip) ? scaled.tooltip[0] : scaled.tooltip
    chart.current?.setOption(
      {
        ...scaled,
        textStyle: { ...scaled.textStyle, fontFamily },
        tooltip: { ...tooltip, textStyle: { ...tooltip?.textStyle, fontFamily } },
      },
      { notMerge: true, lazyUpdate: true },
    )
  }, [option, equalScalePoints, size, fontReady])
  useEffect(() => {
    const instance = chart.current
    if (!instance || !onPointSelect) return
    const select = (event: unknown) => {
      const point = event as { dataIndex?: number; seriesIndex?: number }
      if (point.dataIndex != null && point.seriesIndex != null) {
        onPointSelect(point.dataIndex, point.seriesIndex)
      }
    }
    instance.on('click', select)
    return () => {
      if (!instance.isDisposed()) instance.off('click', select)
    }
  }, [onPointSelect, fontReady])
  useEffect(() => {
    const instance = chart.current
    if (!instance || !onCategorySelect) return
    const select = (event: { offsetX: number; offsetY: number }) => {
      const pixel = [event.offsetX, event.offsetY]
      if (!instance.containPixel({ gridIndex: 0 }, pixel)) return
      const point = instance.convertFromPixel({ gridIndex: 0 }, pixel) as number[]
      if (Number.isFinite(point[0])) onCategorySelect(Math.round(point[0]))
    }
    instance.getZr().on('click', select)
    return () => {
      if (!instance.isDisposed()) instance.getZr().off('click', select)
    }
  }, [onCategorySelect, fontReady])
  return (
    <div
      className="data-chart"
      ref={container}
      role="img"
      aria-label={label}
      style={{ height, width: '100%' }}
    />
  )
}
