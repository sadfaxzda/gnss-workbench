import { describe, expect, it } from 'vitest'
import type { components } from '../generated/api'
import { solutionSummary } from './presentation'

type Solution = components['schemas']['Solution']
const solution = (overrides: Partial<Solution>): Solution => ({
  epoch_id: 1,
  gps_week: 1316,
  gps_sow: 0,
  status: 'VALID',
  n_used: 8,
  processing_ms: 1,
  dof: 4,
  reason: '',
  algorithm: 'consensus',
  search_complete: true,
  ...overrides,
})

describe('solution presentation', () => {
  it('uses current counts even when a saved run has old diagnostic prose', () => {
    expect(
      solutionSummary(solution({ status: 'INVALID_INSUFFICIENT', n_used: 3, reason: '旧版说明' })),
    ).toBe('可用卫星 3 颗 · 最低要求 4 颗')
    expect(solutionSummary(solution({ status: 'NO_OBSERVATIONS', n_used: 0 }))).toBe(
      '本历元无观测数据',
    )
  })

  it('does not claim a passed residual test when detection is off or a statistic is absent', () => {
    const valid = solution({ test_statistic: 2, test_threshold: 10 })
    expect(solutionSummary(valid, false)).toBe('故障检测已关闭')
    expect(solutionSummary(solution({}), true)).toBe('解算完成')
    expect(solutionSummary(valid, true)).toBe('残差检验通过')
  })

  it('keeps incomplete searches and ambiguous hypotheses distinct', () => {
    expect(solutionSummary(solution({ status: 'SUSPECT', search_complete: false }))).toBe(
      '诊断搜索未完成',
    )
    expect(
      solutionSummary(
        solution({ status: 'SUSPECT', candidate_scores: [{ passed: true }, { passed: true }] }),
      ),
    ).toBe('多组候选通过 · 故障卫星待确认')
    expect(solutionSummary(solution({ status: 'SUSPECT' }))).toBe('残差超限 · 故障卫星待确认')
  })
})
