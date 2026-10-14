import type { components } from '../generated/api'
import { format } from './api'

type Solution = components['schemas']['Solution']

export const algorithmLabels: Record<string, string> = {
  ols: '等权最小二乘',
  single_fde: '单星 FDE',
  consensus: '多假设一致性检验',
  adaptive_gnc: '自适应 GNC',
}

// Keep UI summaries separate from persisted diagnostic prose. Full solver
// reasons remain available in exported epoch logs.
export function solutionSummary(solution?: Solution, enableFde?: boolean): string | null {
  if (!solution) return '等待解算'
  switch (solution.status) {
    case 'VALID':
      if (enableFde === false) return '故障检测已关闭'
      return solution.test_statistic != null &&
        solution.test_threshold != null &&
        solution.test_statistic <= solution.test_threshold
        ? '残差检验通过'
        : '解算完成'
    case 'FAULT_EXCLUDED':
      return `剔除 ${(solution.excluded_sats ?? []).join('、')} · 残差检验通过`
    case 'FAULT_MITIGATED':
      return '异常观测已降权'
    case 'INVALID_INSUFFICIENT':
      return `可用卫星 ${solution.n_used} 颗 · 最低要求 4 颗`
    case 'NO_OBSERVATIONS':
      return '本历元无观测数据'
    case 'NO_REDUNDANCY':
      return '残差检验不可用'
    case 'SUSPECT':
      if (solution.search_complete === false) return '诊断搜索未完成'
      if (
        (solution.candidate_scores ?? []).filter((candidate) => candidate.passed === true).length >
        1
      )
        return '多组候选通过 · 故障卫星待确认'
      return '残差超限 · 故障卫星待确认'
    case 'GEOMETRY_WARNING':
      return `PDOP ${format(solution.pdop)}${
        solution.test_statistic != null &&
        solution.test_threshold != null &&
        solution.test_statistic > solution.test_threshold
          ? ' · 残差超限'
          : ''
      }`
    case 'INVALID_CONVERGENCE':
      return '迭代未收敛'
    case 'INVALID_GEOMETRY':
      return '几何矩阵不可解'
    default:
      return solution.reason || null
  }
}
