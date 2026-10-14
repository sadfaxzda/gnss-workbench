import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Check,
  ChevronRight,
  CircleHelp,
  Clock3,
  Database,
  FlaskConical,
  History,
  Layers3,
  Orbit,
  Play,
  Radio,
  Radar,
  Satellite,
  ShieldCheck,
  Square,
  Terminal,
  TriangleAlert,
  Waves,
} from 'lucide-react'
import type { EChartsOption } from 'echarts'
import { Button } from './components/Button'
import { Chart } from './components/Chart'
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
const chartBase: EChartsOption = {
  animation: false,
  color: ['#ec9a4b', '#159d8d'],
  textStyle: { fontFamily: 'Inter, -apple-system, sans-serif', color: '#758190', fontSize: 11 },
  tooltip: { trigger: 'axis', confine: true },
  grid: { left: 53, right: 28, top: 30, bottom: 45 },
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
  icon: Icon,
}: {
  title: string
  value: string
  unit?: string
  note: string
  icon: typeof Satellite
}) {
  return (
    <div className="metric-card">
      <div className="metric-title">
        {title}
        <Icon size={16} />
      </div>
      <div className="metric-value">
        {value}
        <small>{unit}</small>
      </div>
      <div className="metric-note">{note}</div>
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
  const [scenario, setScenario] = useState<Scenario>(initialScenario)
  const [noise, setNoise] = useState(1)
  const [port, setPort] = useState(8765)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
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
  const { epochs, run, connection, transport, error: streamError } = useRunStream(runId)
  const activeRun = runs.find((r) => ['running', 'stopping'].includes(r.status))
  const busy = Boolean(activeRun) || run?.status === 'running' || run?.status === 'stopping'
  const latest = epochs.at(-1)
  const selected =
    selectedIndex == null ? latest : epochs[Math.min(selectedIndex, epochs.length - 1)]
  const solution = selected?.improved
  const metrics = run?.summary.evaluation as Evaluation | undefined
  const stale =
    transport === 'TRANSPORT_STALE' || (run?.status === 'running' && connection === 'disconnected')
  const currentDataset = datasets.find((d) => d.id === (run?.configuration.dataset_id ?? datasetId))
  const total = currentDataset?.epochs ?? 600
  const progress = Math.min(100, (epochs.length / total) * 100)

  function selectRun(id: string) {
    localStorage.setItem('gnss.lastRun', id)
    setRunId(id)
    setSelectedIndex(null)
    setActionError('')
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
          noise_sigma_m: noise,
          scenario,
        }),
      }),
    onSuccess: (result) => {
      selectRun(result.id)
      setPage('live')
      void client.invalidateQueries({ queryKey: ['runs'] })
    },
    onError: (e) => setActionError(e.message),
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
      tooltip: { trigger: 'item', confine: true, formatter: '{a}<br/>{c}' },
      xAxis: {
        type: 'value',
        name: '东 / m',
        nameLocation: 'middle',
        nameGap: 26,
        scale: true,
        splitLine: { lineStyle: { color: '#edf1f4' } },
      },
      yAxis: {
        type: 'value',
        name: '北 / m',
        scale: true,
        splitLine: { lineStyle: { color: '#edf1f4' } },
      },
      series: [
        {
          name: '普通解',
          type: 'line',
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 1.5, opacity: 0.8 },
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
          itemStyle: { color: '#0d7e74', borderColor: '#fff', borderWidth: 2 },
          data: selected?.view.improved_enu ? [selected.view.improved_enu.slice(0, 2)] : [],
        },
      ],
    }),
    [epochs, selected],
  )

  const residualOption = useMemo<EChartsOption>(
    () => ({
      ...chartBase,
      grid: { left: 42, right: 20, top: 20, bottom: 28 },
      tooltip: { trigger: 'axis', confine: true },
      xAxis: {
        type: 'category',
        data: (solution?.diagnostics ?? []).map((s) => s.sat_id),
        axisTick: { show: false },
        axisLine: { show: false },
      },
      yAxis: { type: 'value', name: 'm', splitLine: { lineStyle: { color: '#edf1f4' } } },
      series: [
        {
          type: 'bar',
          barMaxWidth: 22,
          data: (solution?.diagnostics ?? []).map((s) => ({
            value: Number(s.residual_m.toFixed(3)),
            itemStyle: { color: s.excluded ? '#e39648' : '#5eaaa1', borderRadius: [4, 4, 0, 0] },
          })),
        },
      ],
    }),
    [solution],
  )

  const clockOption = useMemo<EChartsOption>(
    () => ({
      ...chartBase,
      grid: { left: 58, right: 25, top: 20, bottom: 30 },
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
        splitLine: { lineStyle: { color: '#edf1f4' } },
      },
      series: [
        {
          name: '接收机钟差距离项',
          type: 'line',
          showSymbol: false,
          connectNulls: false,
          data: epochs.map((e) => e.improved.clock_bias_m),
          lineStyle: { color: '#6089b8', width: 1.7 },
          areaStyle: { color: '#6089b8', opacity: 0.06 },
        },
      ],
    }),
    [epochs],
  )

  const visibleError = actionError || datasetError?.message || streamError || run?.error
  const title = navigation.find((item) => item.id === page)?.label
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Orbit size={26} />
          </div>
          <div>
            <strong>GNSS</strong>
            <span>WORKBENCH</span>
          </div>
        </div>
        <div className="workspace-label">定位与诊断工作台</div>
        <nav aria-label="主导航">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              aria-label={label}
              onClick={() => setPage(id)}
              className={page === id ? 'nav-item active' : 'nav-item'}
            >
              <Icon size={18} />
              <span>{label}</span>
              {page === id && <ChevronRight size={14} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-divider" />
        <div className="sidebar-caption">当前模型</div>
        <div className="model-info">
          <span className="model-dot" />
          <div>
            GPS L1 C1<small>广播星历 · 单点定位</small>
          </div>
        </div>
        <div className="sidebar-bottom">
          <div className="local-indicator">
            <span />
            本地工作空间
          </div>
          <p>计算与数据保存在本机</p>
          <div className="version">
            v0.1.0 <span>科学计算工作台</span>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            工作空间 <ChevronRight size={13} /> <strong>{title}</strong>
          </div>
          <div className="topbar-right">
            <span className="muted">GPS / GPST</span>
            <span className={`connection-dot ${connection === 'connected' ? 'online' : ''}`} />
            <span>
              {connection === 'connected'
                ? '实时连接'
                : connection === 'completed'
                  ? '历史记录'
                  : '本地服务'}
            </span>
          </div>
        </header>
        <div className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">POSITIONING & INTEGRITY</div>
              <h1>{page === 'live' ? '定位与故障诊断' : title}</h1>
              <p>
                {page === 'live'
                  ? '从原始伪距出发，观察定位结果与每一颗卫星的状态。'
                  : page === 'diagnostics'
                    ? '查看残差检验、剔星假设和异常处置依据。'
                    : page === 'experiments'
                      ? '改变观测条件，用同一套算法检验不同故障与消融设置。'
                      : '保留输入、参数、计算结果和完整诊断证据。'}
              </p>
            </div>
            <div className="heading-label">
              <Layers3 size={15} />
              GPS 单系统
              <span className="vertical-divider" />
              双算法对照
            </div>
          </div>

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

          {page !== 'history' && (
            <section className="control-bar" aria-label="运行控制">
              <div className="control-source">
                <div className="control-icon">
                  <Database size={20} />
                </div>
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
                        {d.id} · {d.title}
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
            <>
              <div className="metrics-grid">
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
              <div className="workspace-grid">
                <section className="panel trajectory-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>定位轨迹</h2>
                      <p>局部东—北坐标 · 原点为首次有效改进解</p>
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
                      option={trajectoryOption}
                      height={337}
                      label="普通解与改进解的定位轨迹"
                    />
                    {epochs.length === 0 && (
                      <div className="chart-empty">
                        <Radar size={36} />
                        <strong>等待第一组观测</strong>
                        <span>选择数据后开始运行，轨迹将在这里逐步绘制</span>
                      </div>
                    )}
                  </div>
                  <div className="trajectory-footer">
                    <span>
                      <span className="status-dot" />
                      {epochs.length} 个历元
                    </span>
                    <span>
                      WGS84 / ENU<span className="footer-dot">·</span>单位：米
                    </span>
                  </div>
                </section>
                <section className="panel solution-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>解算状态</h2>
                      <p>{selectedIndex == null ? '最新接收历元' : '正在查看历史历元'}</p>
                    </div>
                    <Radio size={18} className="muted" />
                  </div>
                  <div className="solution-status">
                    <Status value={solution?.status} />
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
                </section>
              </div>
              <div className="lower-grid">
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>逐星残差</h2>
                      <p>橙色表示已剔除卫星</p>
                    </div>
                    <button className="text-button" onClick={() => setPage('diagnostics')}>
                      诊断详情 <ArrowRight size={14} />
                    </button>
                  </div>
                  <Chart option={residualOption} height={193} label="当前历元各颗卫星的伪距残差" />
                </section>
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>接收机钟差</h2>
                      <p>距离项 b = c · Δt · 横轴为历元编号</p>
                    </div>
                    <Clock3 size={17} className="muted" />
                  </div>
                  <Chart option={clockOption} height={193} label="接收机钟差随历元变化" />
                </section>
              </div>
            </>
          )}

          {page === 'diagnostics' && (
            <div className="diagnostic-layout">
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>卫星观测与处置</h2>
                    <p>
                      历元 {selected?.epoch_id ?? '—'} · {solution?.reason || '请先运行一组观测'}
                    </p>
                  </div>
                  <Status value={solution?.status} />
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>卫星</th>
                        <th>高度角</th>
                        <th>方位角</th>
                        <th>残差 / m</th>
                        <th>权重</th>
                        <th>处置</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(solution?.diagnostics ?? []).map((s) => (
                        <tr key={s.sat_id} className={s.excluded ? 'excluded-row' : ''}>
                          <td>
                            <Satellite size={14} />
                            {s.sat_id}
                          </td>
                          <td>{format(s.elevation_deg, 1)}°</td>
                          <td>{format(s.azimuth_deg, 1)}°</td>
                          <td className="mono">{format(s.residual_m, 3)}</td>
                          <td>{s.weight}</td>
                          <td>
                            <span
                              className={`status ${s.excluded ? 'status-warn' : 'status-good'}`}
                            >
                              {s.excluded ? '异常剔除' : '参与定位'}
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
              <section className="panel evidence-panel">
                <div className="panel-heading">
                  <div>
                    <h2>故障诊断证据</h2>
                    <p>全局检验与逐星剔除假设</p>
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
                <p className="explanation">
                  只有一个剔星假设通过残差检验、且剩余观测仍有冗余时，系统才自动剔除该卫星。共同偏差由接收机钟差吸收。
                </p>
                {(solution?.candidate_scores ?? []).map((raw) => {
                  const c = raw as {
                    sat_id: string
                    statistic: number
                    threshold: number
                    passed: boolean
                  }
                  return (
                    <div className="candidate-row" key={c.sat_id}>
                      <span>剔除 {c.sat_id}</span>
                      <div className="candidate-track">
                        <i
                          style={{
                            width: `${Math.min(100, (c.statistic / Math.max(c.threshold, 1)) * 50)}%`,
                            background: c.passed ? '#159d8d' : '#c9d3de',
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
                <div className="info-box">
                  <CircleHelp size={17} />
                  本方法针对单星故障设计；多个相关故障可能无法唯一识别。低残差也不能保证真实误差小。
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
            <section className="panel timeline-panel">
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
                <button className="text-button" onClick={() => setSelectedIndex(null)}>
                  回到最新
                </button>
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
                      <a href={`/api/runs/${run.id}/download/baseline.csv`}>
                        <ArrowDownToLine size={13} />
                        普通解
                      </a>
                      <a href={`/api/runs/${run.id}/download/improved.csv`}>
                        <ArrowDownToLine size={13} />
                        改进解
                      </a>
                      <a href={`/api/runs/${run.id}/download/epochs.jsonl`}>
                        <ArrowDownToLine size={13} />
                        诊断日志
                      </a>
                      <a href={`/api/runs/${run.id}/download/manifest.json`}>
                        <ArrowDownToLine size={13} />
                        实验参数
                      </a>
                    </>
                  )}
                </div>
              </div>
            </section>
          )}
          <footer className="page-footer">
            <span>
              <Terminal size={13} /> GPS L1 C1 · 广播星历 · 等权最小二乘 / 残差一致性诊断
            </span>
            <a href="/api/docs" target="_blank" rel="noreferrer">
              API 文档 <ArrowRight size={12} />
            </a>
          </footer>
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
