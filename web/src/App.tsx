import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Check,
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
import { Skyplot } from './components/Skyplot'
import { SatelliteInspector } from './components/SatelliteInspector'
import { StatusReplay } from './components/StatusReplay'
import { chartBase, chartColors } from './lib/chartTheme'
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
      {value ? statusLabels[value] || value : '尚未运行'}
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
      {scope && <p className="metric-scope">{scope}</p>}
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
  const client = useQueryClient()
  const { data: datasets = [], error: datasetError } = useQuery({
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

  const residualOption = useMemo<EChartsOption>(
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
              borderRadius: [4, 4, 0, 0],
            },
          })),
        },
      ],
    }),
    [solution],
  )

  const clockOption = useMemo<EChartsOption>(
    () => ({
      ...chartBase,
      grid: { left: 58, right: 25, top: 26, bottom: 30 },
      xAxis: {
        type: 'category',
        data: epochs.map((e) => e.epoch_id),
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        scale: true,
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
    [epochs, selected],
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
              数据已过期。下方为历史结果，不能作为当前有效位置。
            </div>
          )}

          {transport === 'TRANSPORT_RESUMED' && !stale && (
            <div className="alert" role="status">
              传输已恢复；当前有效性以最新历元状态为准。
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
                    disabled={busy || scenario.kind !== 'none'}
                  >
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
                  <option value="file">文件逐历元</option>
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
                      <option value="single_fde">原版 · 唯一单星 FDE</option>
                      <option value="consensus">多假设 · 最多两星故障</option>
                      <option value="adaptive_gnc">实验 · 自适应 GNC + 一致性验证</option>
                    </select>
                  </label>
                  <p className="explanation">
                    实验算法参考 ICCV 2025
                    SAC-GNC；当前以鲁棒权重引导假设检验，是否更好需以对照结果判断。
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
                  <p className="explanation">
                    省略星历时使用课程 GPS 周 1316 星历。自定义数据不显示未经真值验证的精度指标。
                  </p>
                  <Button
                    disabled={busy || !importFile || importDataset.isPending}
                    onClick={() => importDataset.mutate()}
                  >
                    {importDataset.isPending ? '正在校验…' : '校验并导入'}
                  </Button>
                </div>
              </details>
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
            <div className="workbench-grid">
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
                  <div className="metrics-grid" aria-label="当前解算指标">
                    <Metric
                      title="参与定位卫星"
                      value={solution ? String(solution.n_used) : '—'}
                      unit="颗"
                      note={solution?.n_used === 4 ? '当前解无观测冗余' : '至少 4 颗完成独立解算'}
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
                          : '有匹配真值的完整运行结束后计算'
                      }
                      icon={ShieldCheck}
                    />
                  </div>

                  <div className="chart-container">
                    <Chart
                      option={trajectoryOption}
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
                        <strong>导入观测，开始定位</strong>
                        <span>选择上方数据源并开始运行，或在设置中导入 JSONL。</span>
                      </div>
                    )}
                  </div>
                  <div className="trajectory-footer">
                    <span>ENU · 首次有效改进解为原点 · 等比例 / 米</span>
                    <span>点击轨迹定位历元</span>
                  </div>
                </section>
                <div className="signal-tray">
                  <section className="panel residual-panel">
                    <div className="panel-heading">
                      <h2>
                        逐星残差 <small>m</small>
                      </h2>
                      <button className="text-button" onClick={() => setPage('diagnostics')}>
                        诊断详情 <ArrowRight size={13} />
                      </button>
                    </div>
                    <Chart
                      option={residualOption}
                      height="100%"
                      label="当前历元各颗卫星的伪距残差"
                      onPointSelect={(index) => {
                        const id = solution?.diagnostics?.[index]?.sat_id
                        if (id) setSatelliteId(id)
                      }}
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
                      option={clockOption}
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
                    <p>{selectedIndex == null ? '最新接收历元' : '正在查看历史历元'}</p>
                  </div>
                </div>
                <div className="solution-status">
                  <Status value={stale ? 'TRANSPORT_STALE' : solution?.status} />
                  <p>{solution?.reason || '运行后显示解算状态与诊断依据。'}</p>
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
                    <span>算法修正距离</span>
                    <strong>
                      {format(selected?.view.correction_m, 3)} <small>m</small>
                    </strong>
                  </div>
                  <span className="correction-icon">
                    <ArrowRight size={19} />
                  </span>
                </div>
                <p className="footnote">修正距离为两种解的三维差值，不代表真实定位误差。</p>
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
          )}

          {page === 'diagnostics' && (
            <div className="diagnostic-layout">
              <section className="panel satellite-panel">
                <div className="panel-heading">
                  <div>
                    <h2>卫星观测与处置</h2>
                    <p>
                      历元 {selected?.epoch_id ?? '—'} · {solution?.reason || '请先运行一组观测'}
                    </p>
                  </div>
                  <Status value={stale ? 'TRANSPORT_STALE' : solution?.status} />
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>卫星</th>
                        <th>高度角</th>
                        <th>方位角</th>
                        <th>残差 / m</th>
                        <th>最终权重</th>
                        <th>鲁棒提议权重</th>
                        <th>处置</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(solution?.diagnostics ?? []).map((s) => (
                        <tr
                          key={s.sat_id}
                          className={`${s.excluded ? 'excluded-row' : ''} ${inspectedSatelliteId === s.sat_id ? 'selected-row' : ''}`}
                        >
                          <td>
                            <button
                              className="satellite-select"
                              aria-label={`查看卫星 ${s.sat_id}`}
                              aria-pressed={inspectedSatelliteId === s.sat_id}
                              onClick={() => setSatelliteId(s.sat_id)}
                            >
                              {s.sat_id}
                            </button>
                          </td>
                          <td>{format(s.elevation_deg, 1)}°</td>
                          <td>{format(s.azimuth_deg, 1)}°</td>
                          <td className="mono">{format(s.residual_m, 3)}</td>
                          <td>{s.weight}</td>
                          <td>{format(s.robust_weight, 3)}</td>
                          <td>
                            <span className={s.excluded ? 'warning-text' : 'muted'}>
                              {s.excluded ? '异常剔除' : s.weight > 0 ? '参与定位' : '未参与定位'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!solution?.diagnostics?.length && (
                    <div className="empty-state">当前历元没有可显示的逐星诊断。</div>
                  )}
                </div>
              </section>
              <section className="panel sky-panel">
                <div className="panel-heading">
                  <div>
                    <h2>卫星天空图</h2>
                    <p>北向为上；内圈60°、中圈30°、外圈0°；红色为剔除卫星</p>
                  </div>
                </div>
                <Skyplot
                  satellites={solution?.diagnostics ?? []}
                  selectedId={inspectedSatelliteId}
                  onSelect={setSatelliteId}
                />
                <SatelliteInspector satellite={satellite} selectedId={inspectedSatelliteId} />
                <p className="explanation">
                  方法：{solution?.algorithm ?? '—'} · 已检验{' '}
                  {solution?.candidate_scores?.length ?? 0} 个假设 · 搜索
                  {!solution ? '—' : solution.search_complete === false ? '未完成' : '完整'}
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
                <div className="evidence-stats">
                  <div>
                    <span>普通解检验统计量</span>
                    <strong>{format(selected?.baseline.test_statistic)}</strong>
                  </div>
                  <div>
                    <span>检验阈值</span>
                    <strong>{format(selected?.baseline.test_threshold)}</strong>
                  </div>
                  <div>
                    <span>改进解检验统计量</span>
                    <strong>{format(solution?.test_statistic)}</strong>
                  </div>
                </div>
                <details className="method-note">
                  <summary>判定规则与方法边界</summary>
                  <p>
                    最小剔星数仅有一个假设通过残差与几何检验，且保留验证冗余时才确认剔除。多个候选通过则保留疑点。共同偏差由钟差吸收。
                  </p>
                </details>
                <div className="candidate-list">
                  {(solution?.candidate_scores ?? []).map((raw) => {
                    const c = raw as {
                      sat_id: string
                      statistic: number | null
                      threshold: number | null
                      passed: boolean
                    }
                    return (
                      <div className="candidate-row" key={c.sat_id}>
                        <span>剔除 {c.sat_id}</span>
                        <div className="candidate-track">
                          <i
                            style={{
                              width: `${Math.min(100, ((c.statistic ?? 0) / Math.max(c.threshold ?? 1, 1)) * 50)}%`,
                              background: c.passed ? chartColors.improved : chartColors.muted,
                            }}
                          />
                        </div>
                        <strong>{format(c.statistic, 1)}</strong>
                        <span className={c.passed ? 'teal-text' : 'muted'}>
                          {c.passed ? '通过' : '未通过'}
                        </span>
                      </div>
                    )
                  })}
                </div>
                <div className="info-box">
                  <CircleHelp size={17} />
                  最多诊断两星故障。相关故障、弱几何与噪声失配仍可能误判。残差通过不等于真实误差小，也不构成完好性保障。
                </div>
              </section>
            </div>
          )}

          {page === 'experiments' && (
            <div className="experiment-grid">
              <section className="panel experiment-form">
                <div className="panel-heading">
                  <div>
                    <h2>受控故障实验</h2>
                    <p>基于 D02 正常仿真数据，按参数修改观测副本</p>
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
                      <option value="none">不注入 · 原始数据</option>
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
                        <span>渐变偏差：从小偏差逐步增加至设置幅度</span>
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
                  <span>原始数据保持完整，参数将写入实验记录</span>
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
                        : '完成一次仿真实验后显示'}
                    </p>
                  </div>
                  <Layers3 size={19} />
                </div>
                <Comparison evaluation={metrics} />
                <div className="info-box">
                  <CircleHelp size={17} />
                  误差指标与有效解比例一起报告。真实历史观测 D01
                  没有独立测量真值，不计算绝对定位精度。
                </div>
                <div className="feature-list">
                  <div>
                    <Check size={16} />
                    相同输入、相同时间范围
                  </div>
                  <div>
                    <Check size={16} />
                    逐历元保留失败与缺测状态
                  </div>
                  <div>
                    <Check size={16} />
                    真值仅用于事后评价
                  </div>
                  <div>
                    <Check size={16} />
                    输入指纹与算法参数可追溯
                  </div>
                </div>
              </section>
            </div>
          )}

          {page === 'history' && (
            <>
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>实验运行记录</h2>
                    <p>点击记录可查看轨迹、诊断证据与评价结果</p>
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
                      <strong>还没有运行记录</strong>
                      <span>每次运行都会自动保存结果与参数。</span>
                      <Button onClick={() => setPage('live')}>开始第一次运行</Button>
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
              <div className="timeline-bottom">
                <div className="run-progress">
                  <Status value={run.status} />
                  <span>
                    {epochs.length}
                    {run.configuration.source === 'file' ? ` / ${total}` : ''} 历元
                  </span>
                  {run.configuration.source === 'file' && (
                    <div className="progress-track">
                      <i style={{ width: `${progress}%` }} />
                    </div>
                  )}
                </div>
                <div className="exports">
                  {!['running', 'stopping'].includes(run.status) && (
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
              </div>
            </section>
          )}
        </div>
      </main>
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
