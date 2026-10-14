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
    throw new Error(
      typeof error.detail === 'string' ? error.detail : `请求未完成 (${response.status})`,
    )
  }
  return response.json() as Promise<T>
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
  return [...byId.values()].sort((a, b) => a.epoch_id - b.epoch_id)
}
