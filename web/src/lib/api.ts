import type { components } from '../generated/api'

export type Run = components['schemas']['RunInfo']
export type RunRequest = components['schemas']['RunRequest']
export type EpochFrame = components['schemas']['EpochFrame']
export type Dataset = components['schemas']['DatasetInfo']
export type Scenario = components['schemas']['FaultScenario']
export type MetricSet = Record<string, number | null>
export type Evaluation = { baseline: MetricSet; improved: MetricSet }

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(requestError(error.detail, response.status))
  }
  return response.json() as Promise<T>
}

export function requestError(detail: unknown, status: number): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    const fields: Record<string, string> = {
      tcp_port: 'TCP 端口',
      noise_sigma_m: '观测噪声',
      jsonl: '观测文件',
      name: '文件名',
      navigation: '广播星历',
      start_epoch: '开始历元',
      duration: '持续历元',
      bias_m: '偏差幅度',
      keep_satellites: '保留卫星数',
      interval_seconds: '回放间隔',
      false_alarm_probability: '虚警概率',
    }
    const issue = detail[0]
    const name = fields[issue.loc?.at(-1)] ?? '运行参数'
    const bound = issue.ctx ?? {}
    const reason =
      issue.type === 'greater_than_equal'
        ? `不得小于 ${bound.ge}`
        : issue.type === 'less_than_equal'
          ? `不得大于 ${bound.le}`
          : issue.type === 'string_too_short'
            ? '不能为空'
            : issue.type === 'string_too_long'
              ? `长度不得超过 ${bound.max_length}`
              : '格式或取值不符合要求'
    return `${name}${reason}，请修改后重试`
  }
  return `请求未完成 (${status})，请重试`
}

export async function requestRunHistory(offset: number, limit: number, query: string) {
  const parameters = new URLSearchParams({ offset: String(offset), limit: String(limit), query })
  const response = await fetch(`/api/runs?${parameters}`)
  if (!response.ok) throw new Error(`运行记录读取失败 (${response.status})，请刷新重试`)
  return {
    items: (await response.json()) as Run[],
    total: Number(response.headers.get('X-Total-Count') ?? 0),
  }
}

export const statusLabels: Record<string, string> = {
  TRANSPORT_STALE: '数据已过期 · 历史位置',
  VALID: '定位有效',
  FAULT_EXCLUDED: '已剔除异常卫星',
  FAULT_MITIGATED: '已抑制异常',
  SUSPECT: '异常待确认',
  NO_REDUNDANCY: '四星 · 无冗余',
  GEOMETRY_WARNING: '几何条件较差',
  INVALID_INSUFFICIENT: '卫星数不足',
  NO_OBSERVATIONS: '无卫星观测',
  INVALID_GEOMETRY: '几何不可解',
  INVALID_CONVERGENCE: '未收敛',
  INVALID_DATA: '数据不可用',
  INVALID_EPHEMERIS: '星历不可用',
  running: '运行中',
  stopping: '正在停止',
  completed: '已完成',
  stopped: '已停止',
  failed: '运行失败',
  interrupted: '运行中断',
}

export function statusTone(status?: string): string {
  if (!status) return 'neutral'
  if (status === 'VALID' || status === 'completed') return 'good'
  if (status === 'FAULT_EXCLUDED' || status === 'running') return 'accent'
  if (status.startsWith('INVALID') || ['NO_OBSERVATIONS', 'failed', 'interrupted'].includes(status))
    return 'bad'
  return 'warn'
}

export function format(value: number | null | undefined, precision = 2): string {
  return value == null || !Number.isFinite(value) ? '—' : value.toFixed(precision)
}

export function upsertEpochs(previous: EpochFrame[], next: EpochFrame[]): EpochFrame[] {
  const byId = new Map(previous.map((epoch) => [epoch.epoch_id, epoch]))
  next.forEach((epoch) => byId.set(epoch.epoch_id, epoch))
  // Epoch IDs are identifiers, not row indices. Preserve acquisition/file order.
  return [...byId.values()]
}
