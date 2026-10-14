import { useEffect, useRef, useState, type ReactNode } from 'react'
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
import { Maximize2, Minimize2, Minus, Plus, RotateCcw } from 'lucide-react'
import type { EChartsOption } from 'echarts'
import { equalAxisBounds, chartColors } from '../lib/chartTheme'
import { fullRange, resizeRange, type ZoomRange } from '../lib/chartSeries'
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
  name,
  onPointSelect,
  onCategorySelect,
  equalScalePoints,
  zoom = 'time',
  range,
  onRangeChange,
  tools,
  expanded,
  onExpand,
}: {
  option: EChartsOption
  height?: number | string
  label: string
  name: string
  onPointSelect?: (index: number, series: number) => void
  onCategorySelect?: (index: number) => void
  equalScalePoints?: number[][]
  zoom?: 'time' | 'plane' | 'category'
  range?: ZoomRange
  onRangeChange?: (range: ZoomRange) => void
  tools?: ReactNode
  expanded?: boolean
  onExpand?: () => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)
  const ranges = useRef<ZoomRange[]>([fullRange, fullRange])
  const dragged = useRef(false)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const [span, setSpan] = useState(100)
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
    const instance = echarts.init(container.current, undefined, { renderer: 'canvas' })
    chart.current = instance
    const observer = new ResizeObserver(([entry]) => {
      instance.resize()
      setSize({ width: entry.contentRect.width, height: entry.contentRect.height })
    })
    observer.observe(container.current)
    let down: number[] | null = null
    const start = (event: { offsetX: number; offsetY: number }) => {
      down = [event.offsetX, event.offsetY]
      dragged.current = false
    }
    const move = (event: { offsetX: number; offsetY: number }) => {
      if (down && Math.hypot(event.offsetX - down[0], event.offsetY - down[1]) > 5)
        dragged.current = true
    }
    const end = () => {
      down = null
    }
    instance.getZr().on('mousedown', start)
    instance.getZr().on('mousemove', move)
    instance.getZr().on('mouseup', end)
    return () => {
      observer.disconnect()
      instance.dispose()
      chart.current = null
    }
  }, [fontReady])
  useEffect(() => {
    const instance = chart.current
    if (!instance) return
    const change = () => {
      const windows = instance.getOption().dataZoom as ZoomRange[]
      ranges.current = windows.map(({ start, end }) => ({ start, end }))
      setSpan(windows[0].end - windows[0].start)
      onRangeChange?.(ranges.current[0])
    }
    instance.on('datazoom', change)
    return () => {
      if (!instance.isDisposed()) instance.off('datazoom', change)
    }
  }, [fontReady, onRangeChange])
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
    const current = range ?? ranges.current[0]
    const inside = {
      type: 'inside' as const,
      filterMode: 'none' as const,
      zoomOnMouseWheel: 'ctrl' as const,
      moveOnMouseWheel: false,
      moveOnMouseMove: true,
      minSpan: 1,
    }
    chart.current?.setOption(
      {
        ...scaled,
        dataZoom: [
          { ...inside, id: 'horizontal', xAxisIndex: 0, ...current },
          ...(zoom === 'plane'
            ? [{ ...inside, id: 'vertical', yAxisIndex: 0, ...ranges.current[1] }]
            : []),
          ...(zoom === 'time'
            ? [
                {
                  type: 'slider' as const,
                  id: 'overview',
                  xAxisIndex: 0,
                  ...current,
                  filterMode: 'none' as const,
                  minSpan: 1,
                  height: 16,
                  bottom: 6,
                  left: 58,
                  right: 25,
                  borderColor: chartColors.grid,
                  backgroundColor: '#f2f3f4',
                  fillerColor: '#355f791a',
                  handleSize: '100%',
                  handleStyle: { color: '#ffffff', borderColor: chartColors.plotAxis },
                  moveHandleSize: 0,
                  showDetail: false,
                  brushSelect: false,
                  dataBackground: {
                    lineStyle: { color: chartColors.baseline },
                    areaStyle: { opacity: 0 },
                  },
                  selectedDataBackground: {
                    lineStyle: { color: chartColors.improved },
                    areaStyle: { opacity: 0 },
                  },
                },
              ]
            : []),
        ],
        textStyle: { ...scaled.textStyle, fontFamily },
        tooltip: { ...tooltip, textStyle: { ...tooltip?.textStyle, fontFamily } },
      },
      { notMerge: true, lazyUpdate: true },
    )
  }, [option, equalScalePoints, size, fontReady, zoom, range])
  useEffect(() => {
    const instance = chart.current
    if (!instance || !onPointSelect) return
    const select = (event: unknown) => {
      const point = event as { dataIndex?: number; seriesIndex?: number }
      if (!dragged.current && point.dataIndex != null && point.seriesIndex != null)
        onPointSelect(point.dataIndex, point.seriesIndex)
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
      if (dragged.current || !instance.containPixel({ gridIndex: 0 }, pixel)) return
      const point = instance.convertFromPixel({ gridIndex: 0 }, pixel) as number[]
      if (Number.isFinite(point[0])) onCategorySelect(Math.round(point[0]))
    }
    instance.getZr().on('click', select)
    return () => {
      if (!instance.isDisposed()) instance.getZr().off('click', select)
    }
  }, [onCategorySelect, fontReady])
  const visibleSpan = range ? range.end - range.start : span
  function changeZoom(factor: number | null) {
    const windows = [range ?? ranges.current[0], ranges.current[1]]
    chart.current?.dispatchAction({
      type: 'dataZoom',
      batch: windows.slice(0, zoom === 'plane' ? 2 : 1).map((window, index) => ({
        dataZoomId: index === 0 ? 'horizontal' : 'vertical',
        ...(factor == null ? fullRange : resizeRange(window, factor)),
      })),
    })
  }
  return (
    <div className="chart-frame" style={{ height }}>
      <div className="chart-toolbar" role="group" aria-label={`${name}图表工具`}>
        <div className="chart-context">
          {tools ?? (
            <span>
              {zoom === 'plane' ? '等比例' : '历元'} ·{' '}
              {visibleSpan > 99.9 ? '全域' : `${(100 / visibleSpan).toFixed(1)}×`}
            </span>
          )}
        </div>
        <div className="chart-actions">
          <button
            className="chart-tool"
            aria-label={`放大${name}`}
            title="放大 · Ctrl + 滚轮"
            disabled={!fontReady || visibleSpan <= 1.01}
            onClick={() => changeZoom(0.5)}
          >
            <Plus size={14} />
          </button>
          <button
            className="chart-tool"
            aria-label={`缩小${name}`}
            title="缩小"
            disabled={!fontReady || visibleSpan >= 99.99}
            onClick={() => changeZoom(2)}
          >
            <Minus size={14} />
          </button>
          <button
            className="chart-tool"
            aria-label={`复位${name}`}
            title="显示全域"
            disabled={!fontReady || visibleSpan >= 99.99}
            onClick={() => changeZoom(null)}
          >
            <RotateCcw size={13} />
          </button>
          {onExpand && (
            <button
              className="chart-tool"
              aria-label={`${expanded ? '收起' : '展开'}${name}`}
              title={expanded ? '返回工作台 · Esc' : '展开图表'}
              aria-pressed={expanded}
              onClick={onExpand}
            >
              {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          )}
        </div>
      </div>
      <div
        className="data-chart"
        ref={container}
        role="img"
        aria-label={label}
        data-zoom-span={visibleSpan.toFixed(3)}
        style={{ width: '100%' }}
      />
    </div>
  )
}
