import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  CircleHelp,
  Clock3,
  FlaskConical,
  History,
  Layers3,
  Orbit,
  Play,
  Radar,
  Satellite,
  ShieldCheck,
  Square,
  TriangleAlert,
  Waves,
} from 'lucide-react'
import type { EChartsOption } from 'echarts'
import { Button } from './components/Button'
import { Chart } from './components/Chart'
import { SatelliteTable } from './components/SatelliteTable'
import { Skyplot } from './components/Skyplot'
import { SatelliteInspector } from './components/SatelliteInspector'
import { StatusReplay } from './components/StatusReplay'
import { chartBase, chartColors } from './lib/chartTheme'
import { fullRange, residualSeries, type ZoomRange } from './lib/chartSeries'
import { algorithmLabels, solutionSummary } from './lib/presentation'
import { useRunStream } from './hooks/useRunStream'
import {
  type Dataset,
  type Evaluation,
  type Run,
  type RunRequest,
  type Scenario,
  format,
  request,
  statusLabels,
  statusTone,
} from './lib/api'

type Page = 'live' | 'diagnostics' | 'experiments' | 'history'
const navigation = [
  { id: 'live', label: '实时定位', icon: Radar },
  { id: 'diagnostics', label: '逐星诊断', icon: Satellite },
  { id: 'experiments', label: '实验设计', icon: FlaskConical },
  { id: 'history', label: '运行记录', icon: History },
] as const
const initialScenario: Scenario = {
  kind: 'none',
  start_epoch: 120,
  duration: 60,
  sat_id: 'G19',
  bias_m: 80,
  ramp: false,
  keep_satellites: 3,
}

function Status({ value }: { value?: string }) {
  return (
    <span className={`status status-${statusTone(value)}`}>
      <span className="status-dot" />
      {value ? statusLabels[value] || value : '待运行'}
    </span>
  )
}

function Metric({
  title,
  value,
  unit,
  note,
  scope,
  icon: Icon,
}: {
  title: string
  value: string
  unit?: string
  note: string
  scope?: string
  icon: typeof Satellite
}) {
  return (
    <div className="metric-card" title={note} tabIndex={0}>
      <div className="metric-title">
        {title}
        <Icon size={16} />
      </div>
      <div className="metric-value">
        {value}
        <small>{unit}</small>
      </div>
      {scope && <span className="metric-scope">{scope}</span>}
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState<Page>('live')
  const [runId, setRunId] = useState<string | null>(() => localStorage.getItem('gnss.lastRun'))
  const [datasetId, setDatasetId] = useState<RunRequest['dataset_id']>('D03_sim_demo')
  const [source, setSource] = useState<'file' | 'tcp'>('file')
  const [interval, setInterval] = useState(0.02)
  const [enableFde, setEnableFde] = useState(true)
  const [algorithm, setAlgorithm] = useState<NonNullable<RunRequest['algorithm']>>('consensus')
  const [importFile, setImportFile] = useState<File | null>(null)
  const [navigationFile, setNavigationFile] = useState<File | null>(null)
  const [scenario, setScenario] = useState<Scenario>(initialScenario)
  const [noise, setNoise] = useState(1)
  const [port, setPort] = useState(8765)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [satelliteId, setSatelliteId] = useState<string | undefined>()
  const [actionError, setActionError] = useState('')
  const [residualMode, setResidualMode] = useState<'trend' | 'satellites'>('trend')
  const [residualSatellite, setResidualSatellite] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState<ZoomRange>(fullRange)
  const [focusedPlot, setFocusedPlot] = useState<'trajectory' | 'residual' | 'clock' | null>(null)
  useEffect(() => {
    const exit = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setFocusedPlot(null)
    }
    window.addEventListener('keydown', exit)
    return () => window.removeEventListener('keydown', exit)
  }, [])
  function focusPlot(plot: 'trajectory' | 'residual' | 'clock') {
    setFocusedPlot((current) => (current === plot ? null : plot))
  }
  const client = useQueryClient()
  const {
    data: datasets = [],
    error: datasetError,
    isPending: datasetsLoading,
  } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => request<Dataset[]>('/datasets'),
  })
  const { data: runs = [] } = useQuery({
    queryKey: ['runs'],
    queryFn: () => request<Run[]>('/runs'),
    refetchInterval: 3000,
  })
  const {
    epochs,
    run,
    connection,
    transport,
    positionStale,
    error: streamError,
  } = useRunStream(runId)
  const activeRun = runs.find((r) => ['running', 'stopping'].includes(r.status))
  const busy = Boolean(activeRun) || run?.status === 'running' || run?.status === 'stopping'
  const latest = epochs.at(-1)
  const selected =
    selectedIndex == null ? latest : epochs[Math.min(selectedIndex, epochs.length - 1)]
  const solution = selected?.improved
  const summary = solutionSummary(solution, run?.configuration.enable_fde)
  const configuredAlgorithm = run?.configuration.algorithm ?? algorithm
  const hasHypothesisSearch =
    solution && ['SUSPECT', 'FAULT_EXCLUDED', 'FAULT_MITIGATED'].includes(solution.status)
  const satellite =
    solution?.diagnostics?.find((item) => item.sat_id === satelliteId) ??
    (satelliteId
      ? undefined
      : (solution?.diagnostics?.find((item) => item.excluded) ?? solution?.diagnostics?.[0]))
  const inspectedSatelliteId = satelliteId ?? satellite?.sat_id
  const metrics = run?.summary.evaluation as Evaluation | undefined
  const stale =
    positionStale ||
    (run?.status === 'running' && ['disconnected', 'connecting'].includes(connection))
  const currentDataset = datasets.find((d) => d.id === (run?.configuration.dataset_id ?? datasetId))
  const total = currentDataset?.epochs ?? 600
  const progress = Math.min(100, (epochs.length / total) * 100)

  function selectRun(id: string) {
    localStorage.setItem('gnss.lastRun', id)
    setRunId(id)
    setSelectedIndex(null)
    setActionError('')
    setSatelliteId(undefined)
    setResidualSatellite(null)
    setTimeRange(fullRange)
  }

  const start = useMutation({
    mutationFn: () =>
      request<Run>('/runs', {
        method: 'POST',
        body: JSON.stringify({
          dataset_id: scenario.kind !== 'none' ? 'D02_sim_clean' : datasetId,
          source,
          interval_seconds: interval,
          tcp_port: port,
          enable_fde: enableFde,
          algorithm,
          noise_sigma_m: noise,
          scenario,
        }),
      }),
    onSuccess: (result) => {
      selectRun(result.id)
      setPage('live')
      document.querySelector<HTMLDetailsElement>('.advanced-controls')?.removeAttribute('open')
      void client.invalidateQueries({ queryKey: ['runs'] })
    },
    onError: (e) => setActionError(e.message),
  })
  const importDataset = useMutation({
    mutationFn: async () => {
      if (!importFile) throw new Error('请选择 JSONL 观测文件')
      if (importFile.size > 16 * 1024 * 1024) throw new Error('导入文件上限为 16 MiB')
      return request<Dataset>('/datasets', {
        method: 'POST',
        body: JSON.stringify({
          name: importFile.name,
          jsonl: await importFile.text(),
          navigation: navigationFile ? JSON.parse(await navigationFile.text()) : null,
        }),
      })
    },
    onSuccess: (dataset) => {
      setDatasetId(dataset.id)
      setSource('file')
      setScenario(initialScenario)
      setActionError('')
      void client.invalidateQueries({ queryKey: ['datasets'] })
    },
    onError: (error) => setActionError(error.message),
  })
  const stop = useMutation({
    mutationFn: () => request<Run>(`/runs/${activeRun?.id ?? runId}/stop`, { method: 'POST' }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['runs'] })
    },
    onError: (e) => setActionError(e.message),
  })

  const trajectoryOption = useMemo<EChartsOption>(
    () => ({
      ...chartBase,
      color: [chartColors.plotBaseline, chartColors.plotImproved],
      textStyle: { ...chartBase.textStyle, color: chartColors.plotText },
      grid: { left: 58, right: 28, top: 30, bottom: 45, outerBoundsMode: 'none' },
      tooltip: { trigger: 'item', confine: true, formatter: '{a}<br/>{c}' },
      xAxis: {
        type: 'value',
        name: '东 / m',
        nameLocation: 'middle',
        nameGap: 26,
        scale: true,
        axisLabel: { showMinLabel: false, showMaxLabel: false, color: chartColors.plotText },
        axisLine: { lineStyle: { color: chartColors.plotAxis } },
        splitLine: { lineStyle: { color: chartColors.plotGrid } },
      },
      yAxis: {
        type: 'value',
        name: '北 / m',
        scale: true,
        axisLabel: { showMinLabel: false, showMaxLabel: false, color: chartColors.plotText },
        axisLine: { lineStyle: { color: chartColors.plotAxis } },
        splitLine: { lineStyle: { color: chartColors.plotGrid } },
      },
      series: [
        {
          name: '普通解',
          type: 'line',
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 1.5, opacity: 0.85, type: 'dashed' },
          data: epochs.map((e) => e.view.baseline_enu?.slice(0, 2) ?? [null, null]),
        },
        {
          name: '改进解',
          type: 'line',
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 2.3 },
          data: epochs.map((e) => e.view.improved_enu?.slice(0, 2) ?? [null, null]),
        },
        {
          name: '选中历元',
          type: 'scatter',
          symbolSize: 10,
          itemStyle: { color: chartColors.plotSelected, borderColor: '#fff', borderWidth: 2 },
          data: selected?.view.improved_enu ? [selected.view.improved_enu.slice(0, 2)] : [],
          tooltip: { show: false },
        },
        {
          name: '历元',
          type: 'scatter',
          symbolSize: 16,
          itemStyle: { color: chartColors.plotImproved, opacity: 0 },
          emphasis: { itemStyle: { opacity: 0.65 } },
          data: epochs.map((e) => e.view.improved_enu?.slice(0, 2) ?? [null, null]),
          tooltip: {
            formatter: (params) => {
              const point = Array.isArray(params) ? params[0] : params
              const epoch = epochs[point.dataIndex]
              return `历元 ${epoch?.epoch_id ?? '—'} · 点击查看`
            },
          },
        },
      ],
    }),
    [epochs, selected],
  )

  const trajectoryPoints = useMemo(
    () =>
      epochs
        .flatMap((epoch) => [epoch.view.baseline_enu, epoch.view.improved_enu])
        .filter((point): point is number[] => point != null),
    [epochs],
  )

  const satelliteResidualOption = useMemo<EChartsOption>(
    () => ({
      ...chartBase,
      grid: { left: 42, right: 20, top: 26, bottom: 28 },
      tooltip: { trigger: 'axis', confine: true },
      xAxis: {
        type: 'category',
        data: (solution?.diagnostics ?? []).map((s) => s.sat_id),
        axisTick: { show: false },
        axisLine: { show: false },
      },
      yAxis: { type: 'value', name: 'm', splitLine: { lineStyle: { color: chartColors.grid } } },
      series: [
        {
          type: 'bar',
          barMaxWidth: 22,
          data: (solution?.diagnostics ?? []).map((s) => ({
            value: Number(s.residual_m.toFixed(3)),
            itemStyle: {
              color: s.excluded ? chartColors.excluded : chartColors.residual,
              borderRadius: 0,
            },
          })),
        },
      ],
    }),
    [solution],
  )

  const residualSatellites = useMemo(
    () =>
      [
        ...new Set(
          epochs.flatMap((epoch) => (epoch.improved.diagnostics ?? []).map((sat) => sat.sat_id)),
        ),
      ].sort(),
    [epochs],
  )
  const targetTickStep = Math.max(1, (epochs.length * (timeRange.end - timeRange.start)) / 600)
  const tickMagnitude = 10 ** Math.floor(Math.log10(targetTickStep))
  const timeTickStep =
    ([1, 2, 5, 10].find((step) => step * tickMagnitude >= targetTickStep) ?? 10) * tickMagnitude
  const residualTrendOption = useMemo<EChartsOption>(() => {
    const values = residualSeries(epochs, residualSatellite)
    return {
      ...chartBase,
      grid: { left: 58, right: 25, top: 28, bottom: 56 },
      tooltip: {
        trigger: 'axis',
        confine: true,
        valueFormatter: (value) => {
          const measurement = Array.isArray(value) ? value[1] : value
          return measurement == null ? '—' : `${Number(measurement).toFixed(3)} m`
        },
      },
      xAxis: {
        type: 'category',
        data: epochs.map((e) => e.epoch_id),
        boundaryGap: false,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          hideOverlap: true,
          interval: (_index, value) => Number(value) % timeTickStep === 0,
        },
      },
      yAxis: {
        type: 'value',
        name: 'm',
        min: residualSatellite ? undefined : 0,
        splitNumber: 4,
        splitLine: { lineStyle: { color: chartColors.grid } },
      },
      series: [
        ...values.map((data, index) => ({
          name: index === 0 ? '普通解' : '改进解',
          type: 'line' as const,
          data,
          showSymbol: false,
          connectNulls: false,
          lineStyle: {
            width: index === 0 ? 1.2 : 1.7,
            type: index === 0 ? ('dashed' as const) : ('solid' as const),
          },
          markLine:
            index === 1 && selected
              ? {
                  silent: true,
                  symbol: 'none',
                  label: { show: false },
                  lineStyle: { color: chartColors.improved, type: 'dashed' as const, width: 1 },
                  data: [{ xAxis: epochs.indexOf(selected) }],
                }
              : undefined,
        })),
        {
          name: '已剔除观测',
          type: 'scatter',
          symbolSize: 4,
          itemStyle: { color: chartColors.excluded },
          data: epochs.map((epoch, index) => {
            const sat = epoch.improved.diagnostics?.find((sat) => sat.sat_id === residualSatellite)
            return [index, sat?.excluded ? sat.residual_m : null]
          }),
        },
      ],
    }
  }, [epochs, residualSatellite, selected, timeTickStep])

  const clockOption = useMemo<EChartsOption>(
    () => ({
      ...chartBase,
      grid: { left: 58, right: 25, top: 26, bottom: 56 },
      xAxis: {
        type: 'category',
        data: epochs.map((e) => e.epoch_id),
        boundaryGap: false,
        axisLabel: {
          hideOverlap: true,
          interval: (_index, value) => Number(value) % timeTickStep === 0,
        },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitNumber: 3,
        axisLabel: { hideOverlap: true },
        name: 'm',
        splitLine: { lineStyle: { color: chartColors.grid } },
      },
      series: [
        {
          name: '接收机钟差距离项',
          type: 'line',
          showSymbol: false,
          connectNulls: false,
          data: epochs.map((e) => e.improved.clock_bias_m),
          lineStyle: { color: chartColors.clock, width: 1.7 },
          markLine: selected
            ? {
                silent: true,
                symbol: 'none',
                label: { show: false },
                lineStyle: { color: chartColors.improved, type: 'dashed', width: 1 },
                data: [{ xAxis: epochs.indexOf(selected) }],
              }
            : undefined,
        },
      ],
    }),
    [epochs, selected, timeTickStep],
  )

  const visibleError = actionError || datasetError?.message || streamError || run?.error
  const title = navigation.find((item) => item.id === page)?.label
  return (
    <div className="app-shell">
      <header className="app-header">
        <a className="brand" href="/" aria-label="GNSS Workbench 首页">
          <Orbit size={23} />
          <strong>
            GNSS<span>Workbench</span>
          </strong>
        </a>
        <nav aria-label="主导航">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              aria-label={label}
              aria-current={page === id ? 'page' : undefined}
              onClick={() => setPage(id)}
              className={page === id ? 'nav-item active' : 'nav-item'}
            >
              <Icon size={16} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="workspace-state">
          <span className={`connection-dot ${connection === 'connected' ? 'online' : ''}`} />
          {connection === 'connected'
            ? '实时连接'
            : connection === 'completed'
              ? '历史回放'
              : '本地工作区'}
          <a
            href="/api/docs"
            target="_blank"
            rel="noreferrer"
            aria-label="API 文档"
            title="API 文档"
          >
            <CircleHelp size={17} />
          </a>
        </div>
      </header>
      <main className="main" data-page={page}>
        <h1 className="sr-only">{page === 'live' ? '定位与故障诊断' : title}</h1>
        <div className="page-content">
          {visibleError && (
            <div className="alert alert-error" role="alert">
              <TriangleAlert size={17} />
              {visibleError}
            </div>
          )}
          {stale && (
            <div className="alert alert-warning" role="status">
              <Clock3 size={17} />
              观测未更新 · 显示上次结果
            </div>
          )}

          {transport === 'TRANSPORT_RESUMED' && !stale && (
            <div className="alert" role="status">
              数据接收已恢复
            </div>
          )}

          {page !== 'history' && (
            <section className="control-bar" aria-label="运行控制">
              <div className="control-source">
                <label>
                  观测数据
                  <select
                    aria-label="观测数据"
                    value={datasetId}
                    onChange={(e) => {
                      setDatasetId(e.target.value as RunRequest['dataset_id'])
                      setScenario(initialScenario)
                    }}
                    disabled={busy || scenario.kind !== 'none' || datasets.length === 0}
                  >
                    {datasets.length === 0 && (
                      <option value="">
                        {datasetsLoading ? '正在加载观测数据…' : '无可用观测数据'}
                      </option>
                    )}
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.title}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="compact-field">
                输入方式
                <select
                  aria-label="输入方式"
                  value={source}
                  onChange={(e) => {
                    setSource(e.target.value as 'file' | 'tcp')
                    setScenario(initialScenario)
                  }}
                  disabled={busy}
                >
                  <option value="file">文件回放</option>
                  <option value="tcp">TCP 实时接入</option>
                </select>
              </label>
              {source === 'file' ? (
                <label className="compact-field">
                  回放速度
                  <select
                    aria-label="回放速度"
                    value={interval}
                    onChange={(e) => setInterval(Number(e.target.value))}
                    disabled={busy}
                  >
                    <option value={1}>1 秒 / 历元</option>
                    <option value={0.1}>0.1 秒 / 历元</option>
                    <option value={0.02}>0.02 秒 / 历元</option>
                    <option value={0}>批量计算</option>
                  </select>
                </label>
              ) : (
                <label className="compact-field">
                  本机端口
                  <input
                    aria-label="TCP端口"
                    type="number"
                    min={1024}
                    max={65535}
                    value={port}
                    disabled={busy}
                    onChange={(e) => setPort(Number(e.target.value))}
                  />
                </label>
              )}
              <details className="panel advanced-controls">
                <summary>
                  <SlidersHorizontal size={15} />
                  算法与自定义数据
                </summary>
                <div className="form-grid">
                  <label>
                    诊断算法
                    <select
                      aria-label="诊断算法"
                      value={algorithm}
                      disabled={busy}
                      onChange={(event) =>
                        setAlgorithm(event.target.value as NonNullable<RunRequest['algorithm']>)
                      }
                    >
                      <option value="single_fde">单星 FDE</option>
                      <option value="consensus">多假设一致性检验</option>
                      <option value="adaptive_gnc">自适应 GNC（实验）</option>
                    </select>
                  </label>
                  <p className="explanation">
                    自适应 GNC：鲁棒权重引导候选搜索，采用一致性检验筛选。
                  </p>
                  <label>
                    观测 JSONL（最多 5000 历元）
                    <input
                      aria-label="导入观测文件"
                      type="file"
                      accept=".jsonl,.json"
                      disabled={busy}
                      onChange={(event) => setImportFile(event.target.files?.[0] ?? null)}
                    />
                  </label>
                  <label>
                    配套星历 JSON（可选）
                    <input
                      aria-label="导入星历文件"
                      type="file"
                      accept=".json"
                      disabled={busy}
                      onChange={(event) => setNavigationFile(event.target.files?.[0] ?? null)}
                    />
                  </label>
                  <p className="explanation">未选择配套星历时，使用内置 GPS 周 1316 星历。</p>
                  <Button
                    disabled={busy || !importFile || importDataset.isPending}
                    onClick={() => importDataset.mutate()}
                  >
                    {importDataset.isPending ? '正在校验…' : '校验并导入'}
                  </Button>
                </div>
              </details>
              {run && !['running', 'stopping'].includes(run.status) ? (
                <details
                  className="export-menu"
                  onKeyDown={(event) => {
                    if (event.key === 'Escape') {
                      event.currentTarget.open = false
                      event.currentTarget.querySelector('summary')?.focus()
                    }
                  }}
                  onBlur={(event) => {
                    if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget))
                      event.currentTarget.open = false
                  }}
                >
                  <summary>
                    <ArrowDownToLine size={14} />
                    导出结果
                  </summary>
                  <div className="exports">
                    {run && (
                      <>
                        <a href={`/api/runs/${run.id}/download/baseline.csv`} download>
                          <ArrowDownToLine size={13} />
                          普通解
                        </a>
                        <a href={`/api/runs/${run.id}/download/improved.csv`} download>
                          <ArrowDownToLine size={13} />
                          改进解
                        </a>
                        <a href={`/api/runs/${run.id}/download/epochs.jsonl`} download>
                          <ArrowDownToLine size={13} />
                          诊断日志
                        </a>
                        <a href={`/api/runs/${run.id}/download/input.jsonl`} download>
                          <ArrowDownToLine size={13} />
                          观测输入
                        </a>
                        <a href={`/api/runs/${run.id}/download/navigation.json`} download>
                          <ArrowDownToLine size={13} />
                          配套星历
                        </a>
                        <a href={`/api/runs/${run.id}/download/manifest.json`} download>
                          <ArrowDownToLine size={13} />
                          实验参数
                        </a>
                      </>
                    )}
                  </div>
                </details>
              ) : (
                <button className="export-disabled" disabled>
                  <ArrowDownToLine size={14} />
                  导出结果
                </button>
              )}
              <div className="control-actions">
                {busy && runId ? (
                  <Button variant="outline" onClick={() => stop.mutate()} disabled={stop.isPending}>
                    <Square size={14} />
                    停止运行
                  </Button>
                ) : (
                  <Button
                    onClick={() => {
                      setActionError('')
                      start.mutate()
                    }}
                    disabled={start.isPending || datasets.length === 0}
                  >
                    <Play size={15} fill="currentColor" />
                    {start.isPending ? '正在启动…' : '开始运行'}
                  </Button>
                )}
              </div>
            </section>
          )}

          {page === 'live' && (
            <div className="live-workspace">
              <div className="metrics-grid" aria-label="当前解算指标">
                <Metric
                  title="参与解算卫星"
                  value={solution ? String(solution.n_used) : '—'}
                  unit="颗"
                  note="当前历元参与解算的卫星数"
                  icon={Satellite}
                />
                <Metric
                  title="位置精度因子"
                  value={format(solution?.pdop)}
                  unit="PDOP"
                  note="由未加权卫星几何矩阵计算"
                  icon={Orbit}
                />
                <Metric
                  title="后验残差"
                  value={format(solution?.residual_rms_m)}
                  unit="m"
                  note="实际参与解算观测的 RMS"
                  icon={Waves}
                />
                <Metric
                  title="水平误差 P95"
                  scope="仿真 · 全程"
                  value={format(metrics?.improved.h_p95_m)}
                  unit="m"
                  note={
                    metrics
                      ? `仿真评价 · 有效解比例 ${format((metrics.improved.availability_on_required ?? 0) * 100, 1)}%`
                      : '运行结束后按参考真值计算'
                  }
                  icon={ShieldCheck}
                />
              </div>

              <div className="workbench-grid" data-focus={focusedPlot ?? undefined}>
                <div className="plot-workspace">
                  <section className="panel trajectory-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>定位轨迹</h2>
                        <span className="run-reference">
                          {currentDataset?.title ?? '选择观测数据'}
                          {run && ` / ${run.id.slice(0, 8)}`}
                        </span>
                      </div>
                      <div className="legend">
                        <span>
                          <i className="orange" />
                          普通解
                        </span>
                        <span>
                          <i className="teal" />
                          改进解
                        </span>
                      </div>
                    </div>
                    <div className="chart-container">
                      <Chart
                        key={runId}
                        name="定位轨迹"
                        option={trajectoryOption}
                        zoom="plane"
                        expanded={focusedPlot === 'trajectory'}
                        onExpand={() => focusPlot('trajectory')}
                        height="100%"
                        label="普通解与改进解的定位轨迹"
                        equalScalePoints={trajectoryPoints}
                        onPointSelect={(index, series) => {
                          if (series === 3) setSelectedIndex(index)
                        }}
                      />
                      {epochs.length === 0 && (
                        <div className="chart-empty">
                          <Radar size={28} />
                          <strong>暂无定位结果</strong>
                          <span>选择观测数据，开始运行。</span>
                        </div>
                      )}
                    </div>
                    <div className="trajectory-footer">
                      <span>ENU · 首次有效改进解为原点</span>
                      <span>点击定位历元 · 拖动平移</span>
                    </div>
                  </section>
                  <div className="signal-tray">
                    <section className="panel residual-panel">
                      <div className="panel-heading">
                        <h2>
                          {residualMode === 'trend' ? '残差趋势' : '逐星残差'} <small>m</small>
                        </h2>
                        <div
                          className="legend residual-legend"
                          style={{ visibility: residualMode === 'trend' ? 'visible' : 'hidden' }}
                        >
                          <span>
                            <i className="orange" />
                            普通解
                          </span>
                          <span>
                            <i className="teal" />
                            改进解
                          </span>
                        </div>
                        <button className="text-button" onClick={() => setPage('diagnostics')}>
                          诊断详情 <ArrowRight size={13} />
                        </button>
                      </div>
                      <Chart
                        key={`${runId}-${residualMode}`}
                        name="残差图"
                        option={
                          residualMode === 'trend' ? residualTrendOption : satelliteResidualOption
                        }
                        height="100%"
                        zoom={residualMode === 'trend' ? 'time' : 'category'}
                        range={residualMode === 'trend' ? timeRange : undefined}
                        onRangeChange={residualMode === 'trend' ? setTimeRange : undefined}
                        expanded={focusedPlot === 'residual'}
                        onExpand={() => focusPlot('residual')}
                        tools={
                          <>
                            <div className="view-switch" aria-label="残差视图">
                              <button
                                aria-pressed={residualMode === 'trend'}
                                onClick={() => setResidualMode('trend')}
                              >
                                时间趋势
                              </button>
                              <button
                                aria-pressed={residualMode === 'satellites'}
                                onClick={() => setResidualMode('satellites')}
                              >
                                逐星对比
                              </button>
                            </div>
                            {residualMode === 'trend' && (
                              <select
                                aria-label="残差趋势观测量"
                                value={residualSatellite ?? ''}
                                onChange={(event) => {
                                  setResidualSatellite(event.target.value || null)
                                  if (event.target.value) setSatelliteId(event.target.value)
                                }}
                              >
                                <option value="">总体 RMS</option>
                                {residualSatellites.map((id) => (
                                  <option key={id} value={id}>
                                    {id}
                                  </option>
                                ))}
                              </select>
                            )}
                          </>
                        }
                        label={
                          residualMode === 'trend'
                            ? '普通解与改进解的残差时间趋势'
                            : '当前历元各颗卫星的伪距残差'
                        }
                        onCategorySelect={
                          residualMode === 'trend'
                            ? (index) =>
                                setSelectedIndex(Math.max(0, Math.min(index, epochs.length - 1)))
                            : undefined
                        }
                        onPointSelect={
                          residualMode === 'satellites'
                            ? (index) => {
                                const id = solution?.diagnostics?.[index]?.sat_id
                                if (id) setSatelliteId(id)
                              }
                            : undefined
                        }
                      />
                    </section>
                    <section className="panel clock-panel">
                      <div className="panel-heading">
                        <h2>
                          接收机钟差 <small>m</small>
                        </h2>
                        <span className="muted">b = c · Δt</span>
                      </div>
                      <Chart
                        key={runId}
                        name="接收机钟差"
                        option={clockOption}
                        range={timeRange}
                        onRangeChange={setTimeRange}
                        expanded={focusedPlot === 'clock'}
                        onExpand={() => focusPlot('clock')}
                        height="100%"
                        label="接收机钟差随历元变化"
                        onCategorySelect={(index) =>
                          setSelectedIndex(Math.max(0, Math.min(index, epochs.length - 1)))
                        }
                      />
                    </section>
                  </div>
                </div>
                <section className="panel solution-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>解算状态</h2>
                      <p>
                        {selectedIndex == null ? '最新历元' : `历元 ${selected?.epoch_id ?? '—'}`}
                      </p>
                    </div>
                  </div>
                  <div className="solution-status">
                    <Status value={stale ? 'TRANSPORT_STALE' : solution?.status} />
                    {summary && <p>{summary}</p>}
                  </div>
                  <dl className={stale ? 'position-details stale' : 'position-details'}>
                    <div>
                      <dt>纬度</dt>
                      <dd>
                        {format(selected?.view.latitude_deg, 7)}
                        <small>°</small>
                      </dd>
                    </div>
                    <div>
                      <dt>经度</dt>
                      <dd>
                        {format(selected?.view.longitude_deg, 7)}
                        <small>°</small>
                      </dd>
                    </div>
                    <div>
                      <dt>椭球高</dt>
                      <dd>
                        {format(selected?.view.height_m, 3)}
                        <small>m</small>
                      </dd>
                    </div>
                    <div>
                      <dt>接收机钟差</dt>
                      <dd>
                        {format(solution?.clock_bias_m, 3)}
                        <small>m</small>
                      </dd>
                    </div>
                    <div>
                      <dt>单历元计算</dt>
                      <dd>
                        {format(solution?.processing_ms, 2)}
                        <small>ms</small>
                      </dd>
                    </div>
                  </dl>
                  <div className="correction">
                    <div>
                      <span>三维解差</span>
                      <strong>
                        {format(selected?.view.correction_m, 3)} <small>m</small>
                      </strong>
                    </div>
                    <span className="correction-icon">
                      <ArrowRight size={19} />
                    </span>
                  </div>
                  <div className="inspector-sky">
                    <div className="inspector-heading">
                      <h3>卫星分布</h3>
                      <span>点击选择卫星</span>
                    </div>
                    <Skyplot
                      satellites={solution?.diagnostics ?? []}
                      selectedId={inspectedSatelliteId}
                      onSelect={setSatelliteId}
                    />
                  </div>
                  <SatelliteInspector satellite={satellite} selectedId={inspectedSatelliteId} />
                </section>
              </div>
            </div>
          )}

          {page === 'diagnostics' && (
            <div className="diagnostic-layout">
              <section className="panel satellite-panel">
                <div className="panel-heading">
                  <div>
                    <h2>卫星观测与处置</h2>
                    <p>
                      历元 {selected?.epoch_id ?? '—'}
                      {summary && ` · ${summary}`}
                    </p>
                  </div>
                  <Status value={stale ? 'TRANSPORT_STALE' : solution?.status} />
                </div>
                <SatelliteTable
                  satellites={solution?.diagnostics ?? []}
                  selectedId={inspectedSatelliteId}
                  onSelect={setSatelliteId}
                />
              </section>
              <section className="panel sky-panel">
                <div className="panel-heading">
                  <div>
                    <h2>卫星天空图</h2>
                    <p>高度角 0° / 30° / 60° · 北向为上</p>
                  </div>
                </div>
                <Skyplot
                  satellites={solution?.diagnostics ?? []}
                  selectedId={inspectedSatelliteId}
                  onSelect={setSatelliteId}
                />
                <SatelliteInspector satellite={satellite} selectedId={inspectedSatelliteId} />
                <p className="explanation">
                  {algorithmLabels[configuredAlgorithm] ?? configuredAlgorithm} ·{' '}
                  {hasHypothesisSearch
                    ? `检验 ${solution.candidate_scores?.length ?? 0} 个假设 · 搜索${solution.search_complete === false ? '未完成' : '完成'}`
                    : '假设检验未执行'}
                </p>
                {!!solution?.algorithm_trace?.length && (
                  <details>
                    <summary>GNC 搜索轨迹 · {solution.algorithm_trace.length} 个提议</summary>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>深度</th>
                            <th>退火率</th>
                            <th>尺度 / m</th>
                            <th>MSAC / m²</th>
                          </tr>
                        </thead>
                        <tbody>
                          {solution.algorithm_trace.map((raw, index) => {
                            const trace = raw as {
                              depth: number
                              annealing_rate: number
                              shape_m: number
                              msac_score_m2: number
                            }
                            return (
                              <tr key={index}>
                                <td>{trace.depth}</td>
                                <td>{trace.annealing_rate}</td>
                                <td>{format(trace.shape_m)}</td>
                                <td>{format(trace.msac_score_m2)}</td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )}
              </section>
              <section className="panel evidence-panel">
                <div className="panel-heading">
                  <div>
                    <h2>故障诊断证据</h2>
                    <p>全局检验与最小故障数假设</p>
                  </div>
                  <ShieldCheck size={20} className="teal-text" />
                </div>
                <div className="table-scroll evidence-summary">
                  <table aria-label="全局检验结果">
                    <thead>
                      <tr>
                        <th>解算方案</th>
                        <th className="numeric">检验统计量</th>
                        <th className="numeric">检验阈值</th>
                        <th className="numeric">自由度</th>
                        <th>残差检验</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(
                        [
                          ['普通解', selected?.baseline],
                          ['改进解', solution],
                        ] as const
                      ).map(([label, result]) => (
                        <tr key={label}>
                          <th scope="row">{label}</th>
                          <td className="numeric">{format(result?.test_statistic)}</td>
                          <td className="numeric">{format(result?.test_threshold)}</td>
                          <td className="numeric">{result?.dof ?? '—'}</td>
                          <td>
                            {result?.test_statistic != null && result?.test_threshold != null
                              ? result.test_statistic <= result.test_threshold
                                ? '通过'
                                : '未通过'
                              : result?.status === 'NO_REDUNDANCY'
                                ? '无冗余'
                                : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <details className="method-note">
                  <summary>诊断方法</summary>
                  <p>
                    按最少剔星数检验候选解。候选唯一、残差与几何检验通过且保留验证冗余时，剔除对应观测。
                  </p>
                  <p>
                    诊断范围：{configuredAlgorithm === 'single_fde' ? '单星' : '单星与双星'}
                    假设。观测共同偏差计入接收机钟差。
                  </p>
                </details>
                {!!solution?.candidate_scores?.length && (
                  <div className="table-scroll hypothesis-table">
                    <table aria-label="候选假设检验">
                      <thead>
                        <tr>
                          <th>排除卫星</th>
                          <th className="numeric">检验统计量</th>
                          <th className="numeric">检验阈值</th>
                          <th>判定</th>
                        </tr>
                      </thead>
                      <tbody>
                        {solution.candidate_scores.map((raw) => {
                          const c = raw as {
                            sat_id: string
                            statistic: number | null
                            threshold: number | null
                            passed: boolean
                          }
                          return (
                            <tr key={c.sat_id}>
                              <th scope="row">{c.sat_id}</th>
                              <td className="numeric">{format(c.statistic)}</td>
                              <td className="numeric">{format(c.threshold)}</td>
                              <td>{c.passed ? '通过' : '未通过'}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </div>
          )}

          {page === 'experiments' && (
            <div className="experiment-grid">
              <section className="panel experiment-form">
                <div className="panel-heading">
                  <div>
                    <h2>受控故障实验</h2>
                    <p>数据源：D02 · 正常仿真观测</p>
                  </div>
                  <FlaskConical size={20} className="teal-text" />
                </div>
                <div className="form-grid">
                  <label className="wide">
                    故障类型
                    <select
                      aria-label="故障类型"
                      disabled={busy || source === 'tcp'}
                      value={scenario.kind}
                      onChange={(e) => {
                        setScenario({ ...scenario, kind: e.target.value as Scenario['kind'] })
                        setDatasetId('D02_sim_clean')
                      }}
                    >
                      <option value="none">无故障注入</option>
                      <option value="satellite_bias">单星伪距偏差</option>
                      <option value="common_bias">全星共同偏差</option>
                      <option value="dropout">卫星观测缺失</option>
                    </select>
                  </label>
                  <label>
                    开始历元
                    <input
                      aria-label="开始历元"
                      type="number"
                      min={0}
                      max={599}
                      value={scenario.start_epoch}
                      disabled={busy}
                      onChange={(e) =>
                        setScenario({ ...scenario, start_epoch: Number(e.target.value) })
                      }
                    />
                  </label>
                  <label>
                    持续历元
                    <input
                      aria-label="持续历元"
                      type="number"
                      min={1}
                      max={600}
                      value={scenario.duration}
                      disabled={busy}
                      onChange={(e) =>
                        setScenario({ ...scenario, duration: Number(e.target.value) })
                      }
                    />
                  </label>
                  {scenario.kind === 'dropout' ? (
                    <label className="wide">
                      保留卫星数量
                      <input
                        aria-label="保留卫星数量"
                        type="number"
                        min={0}
                        max={8}
                        value={scenario.keep_satellites}
                        disabled={busy}
                        onChange={(e) =>
                          setScenario({ ...scenario, keep_satellites: Number(e.target.value) })
                        }
                      />
                    </label>
                  ) : (
                    <>
                      <label>
                        目标卫星
                        <select
                          aria-label="目标卫星"
                          value={scenario.sat_id}
                          disabled={busy || scenario.kind !== 'satellite_bias'}
                          onChange={(e) => setScenario({ ...scenario, sat_id: e.target.value })}
                        >
                          {['G03', 'G07', 'G08', 'G11', 'G19', 'G20', 'G24', 'G28'].map((s) => (
                            <option key={s}>{s}</option>
                          ))}
                        </select>
                      </label>
                      <label>
                        偏差幅度 / m
                        <input
                          aria-label="偏差幅度"
                          type="number"
                          min={-1000}
                          max={1000}
                          value={scenario.bias_m}
                          disabled={busy}
                          onChange={(e) =>
                            setScenario({ ...scenario, bias_m: Number(e.target.value) })
                          }
                        />
                      </label>
                      <label className="check-row wide">
                        <input
                          type="checkbox"
                          checked={scenario.ramp}
                          disabled={busy}
                          onChange={(e) => setScenario({ ...scenario, ramp: e.target.checked })}
                        />
                        <span>
                          渐变偏差 <small>线性增加至设定幅度</small>
                        </span>
                      </label>
                    </>
                  )}
                  <label className="wide">
                    观测噪声先验 σ / m
                    <input
                      aria-label="噪声先验"
                      type="number"
                      min={0.1}
                      max={20}
                      step={0.1}
                      value={noise}
                      disabled={busy}
                      onChange={(e) => setNoise(Number(e.target.value))}
                    />
                  </label>
                  <label className="check-row wide">
                    <input
                      type="checkbox"
                      checked={enableFde}
                      disabled={busy}
                      onChange={(e) => setEnableFde(e.target.checked)}
                    />
                    <span>
                      启用故障检测与剔除 <small>关闭可进行消融实验</small>
                    </span>
                  </label>
                </div>
                <div className="form-footer">
                  <span>参数随运行结果保存</span>
                  <Button
                    onClick={() => start.mutate()}
                    disabled={busy || start.isPending || source === 'tcp'}
                  >
                    <Play size={15} />
                    运行实验
                  </Button>
                </div>
              </section>
              <section className="panel compare-panel">
                <div className="panel-heading">
                  <div>
                    <h2>最近运行对比</h2>
                    <p>
                      {run
                        ? `${run.configuration.dataset_id} · ${run.id.slice(0, 8)}`
                        : '暂无评价结果'}
                    </p>
                  </div>
                  <Layers3 size={19} />
                </div>
                <Comparison evaluation={metrics} />
                {!metrics && (
                  <p className="explanation">
                    {run?.configuration.dataset_id === 'D01_real_excerpt'
                      ? 'D01 未配置参考真值'
                      : '运行结束后生成评价结果'}
                  </p>
                )}
              </section>
            </div>
          )}

          {page === 'history' && (
            <>
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>实验运行记录</h2>
                    <p>保存的输入、参数与解算结果</p>
                  </div>
                  <span className="count-badge">{runs.length} 次运行</span>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>运行编号</th>
                        <th>数据集</th>
                        <th>创建时间</th>
                        <th>历元</th>
                        <th>状态</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {runs.map((r) => (
                        <tr key={r.id}>
                          <td className="mono">{r.id.slice(0, 8)}</td>
                          <td>
                            {r.configuration.dataset_id}
                            <small className="table-sub">
                              {r.configuration.scenario?.kind !== 'none'
                                ? '受控故障实验'
                                : r.configuration.enable_fde
                                  ? '基线 + 故障诊断'
                                  : '消融实验'}
                            </small>
                          </td>
                          <td>
                            {new Date(r.created_at).toLocaleString('zh-CN', { hour12: false })}
                          </td>
                          <td>{r.epoch_count}</td>
                          <td>
                            <Status value={r.status} />
                          </td>
                          <td>
                            <Button
                              variant="ghost"
                              onClick={() => {
                                selectRun(r.id)
                                setPage('live')
                              }}
                            >
                              查看 <ArrowRight size={14} />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {runs.length === 0 && (
                    <div className="empty-state">
                      <History size={28} />
                      <strong>暂无运行记录</strong>
                      <span>运行结果与参数自动保存。</span>
                      <Button onClick={() => setPage('live')}>新建运行</Button>
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          {page !== 'history' && run && (
            <section className="panel timeline-panel" aria-label="统一历元回放">
              <StatusReplay
                epochs={epochs}
                selectedIndex={selectedIndex}
                onSelect={setSelectedIndex}
              />
              <div className="timeline-top">
                <div>
                  <Activity size={16} />
                  <strong>
                    {selectedIndex == null ? '跟随最新历元' : `查看历元 ${selected?.epoch_id}`}
                  </strong>
                  <span className="mono">
                    {selected?.improved.gps_week ?? '—'} / {format(selected?.improved.gps_sow, 3)}{' '}
                    GPST
                  </span>
                </div>
                <div className="epoch-actions">
                  <button
                    className="icon-button"
                    aria-label="上一个历元"
                    title="上一个历元"
                    disabled={!epochs.length || (selectedIndex ?? epochs.length - 1) === 0}
                    onClick={() =>
                      setSelectedIndex(Math.max(0, (selectedIndex ?? epochs.length - 1) - 1))
                    }
                  >
                    <ChevronLeft size={15} />
                  </button>
                  <button
                    className="icon-button"
                    aria-label="下一个历元"
                    title="下一个历元"
                    disabled={
                      !epochs.length || (selectedIndex ?? epochs.length - 1) >= epochs.length - 1
                    }
                    onClick={() =>
                      setSelectedIndex(
                        Math.min(epochs.length - 1, (selectedIndex ?? epochs.length - 1) + 1),
                      )
                    }
                  >
                    <ChevronRight size={15} />
                  </button>
                  <button className="text-button" onClick={() => setSelectedIndex(null)}>
                    回到最新
                  </button>
                </div>
              </div>
              <input
                aria-label="历元时间轴"
                className="timeline-slider"
                type="range"
                min={0}
                max={Math.max(0, epochs.length - 1)}
                value={selectedIndex ?? Math.max(0, epochs.length - 1)}
                onChange={(e) => setSelectedIndex(Number(e.target.value))}
                disabled={epochs.length === 0}
              />
            </section>
          )}
        </div>
      </main>
      <footer className="app-statusbar" aria-label="应用状态栏">
        <div className="statusbar-field">
          {run ? <Status value={run.status} /> : <span>就绪</span>}
        </div>
        {run && (
          <div className="statusbar-field">
            <span>
              {epochs.length}
              {run.configuration.source === 'file' ? ` / ${total}` : ''} 历元
            </span>
            {['running', 'stopping'].includes(run.status) &&
              run.configuration.source === 'file' && (
                <progress aria-label="解算进度" value={progress} max={100} />
              )}
          </div>
        )}
        <div className="statusbar-field statusbar-context">
          {run
            ? `${run.configuration.source === 'file' ? '文件回放' : 'TCP 接入'} · ${algorithmLabels[configuredAlgorithm] ?? configuredAlgorithm}`
            : '选择观测数据后开始运行'}
        </div>
        <div className="statusbar-field statusbar-reference">
          WGS 84<span>GPST</span>
          <span>m</span>
        </div>
      </footer>
    </div>
  )
}

function Comparison({ evaluation }: { evaluation?: Evaluation }) {
  const fields = [
    ['水平误差 P95', 'h_p95_m', 'm', 1],
    ['有效解比例', 'availability_on_required', '%', 100],
    ['10 m 内成功比例', 'success_within_10m_on_required', '%', 100],
    ['强故障检出率', 'fault_detection_recall', '%', 100],
    ['正常历元误报率', 'false_alarm_epoch_rate', '%', 100],
  ] as const
  return (
    <table className="comparison-table">
      <thead>
        <tr>
          <th>评价指标</th>
          <th>
            <i className="legend-dot orange" />
            普通解
          </th>
          <th>
            <i className="legend-dot teal" />
            改进解
          </th>
        </tr>
      </thead>
      <tbody>
        {fields.map(([label, key, unit, multiplier]) => (
          <tr key={key}>
            <td>{label}</td>
            {(['baseline', 'improved'] as const).map((mode) => {
              const v = evaluation?.[mode][key]
              return (
                <td key={mode} className={mode === 'improved' ? 'teal-text mono' : 'mono'}>
                  {format(v == null ? null : v * multiplier)}
                  <small> {unit}</small>
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
