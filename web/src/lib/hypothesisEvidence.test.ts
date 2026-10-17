import { expect, it } from 'vitest'
import type { components } from '../generated/api'
import { adoptedCandidate, hypothesisEvidence } from './hypothesisEvidence'

type Solution = components['schemas']['Solution']
const solution = (overrides: Partial<Solution> = {}): Solution => ({
  epoch_id: 1,
  gps_week: 1316,
  gps_sow: 100,
  status: 'SUSPECT',
  n_used: 5,
  processing_ms: 1,
  dof: 1,
  reason: '',
  algorithm: 'consensus',
  search_complete: true,
  excluded_sats: ['G07'],
  ...overrides,
})

it('uses actual exclusions when older records omit or contradict the selected flag', () => {
  const s = solution({
    algorithm: 'single_fde',
    status: 'FAULT_EXCLUDED',
    candidate_scores: [{ sat_id: 'G03', selected: true }, { sat_id: 'G07' }],
  })
  expect(adoptedCandidate(s, { sat_id: 'G03', selected: true })).toBe(false)
  expect(hypothesisEvidence(s)).toMatchObject({
    satellites: 'G07',
    source: '单星排除检验',
    logRatio: null,
    epochs: null,
  })
  expect(
    hypothesisEvidence(
      solution({ excluded_sats: [], candidate_scores: [{ sat_id: 'G07', selected: true }] }),
    ),
  ).toBeNull()
})

it('does not display a different historical winner score for a current provisional choice', () => {
  const evidence = hypothesisEvidence(
    solution({
      candidate_scores: [
        {
          sat_id: 'G07',
          selection_method: 'provisional_likelihood',
          provisional_source: 'current',
          evidence_epochs: 16,
          current_likelihood_share: 0.5,
          selection_log_ratio: 15,
          required_log_ratio: Math.log(20),
          history_sigma_m: 1,
        },
      ],
    }),
  )
  expect(evidence).toMatchObject({ epochs: 1, logRatio: 0, provisional: true })
})

it('a large historical proposal score cannot change the displayed confirmation state', () => {
  const evidence = hypothesisEvidence(
    solution({
      candidate_scores: [
        {
          sat_id: 'G07',
          selection_method: 'provisional_likelihood',
          provisional_source: 'coherent_proposal',
          evidence_epochs: 16,
          selection_log_ratio: 12,
          required_log_ratio: Math.log(20),
        },
      ],
    }),
  )
  expect(evidence).toMatchObject({
    source: '历史偏差提议（仅暂定）',
    epochs: 16,
    logRatio: 12,
    provisional: true,
    historySigma: null,
  })
})
