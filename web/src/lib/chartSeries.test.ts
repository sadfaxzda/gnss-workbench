import { describe, expect, it } from 'vitest'
import type { EpochFrame } from './api'
import { residualSeries, resizeRange } from './chartSeries'

describe('residual time series', () => {
  it('preserves missing epoch slots and excluded observations in a satellite trace', () => {
    const frames = [
      {
        baseline: { residual_rms_m: 8, diagnostics: [{ sat_id: 'G19', residual_m: 12 }] },
        improved: {
          residual_rms_m: 1,
          diagnostics: [{ sat_id: 'G19', residual_m: 80, excluded: true }],
        },
      },
      { baseline: { residual_rms_m: null }, improved: { residual_rms_m: null } },
      {
        baseline: { residual_rms_m: 0.5, diagnostics: [{ sat_id: 'G20', residual_m: 0.2 }] },
        improved: { residual_rms_m: 0.5, diagnostics: [{ sat_id: 'G20', residual_m: 0.2 }] },
      },
    ] as unknown as EpochFrame[]
    expect(residualSeries(frames, 'G19')).toEqual([
      [12, null, null],
      [80, null, null],
    ])
    expect(residualSeries(frames, null)).toEqual([
      [8, null, 0.5],
      [1, null, 0.5],
    ])
    expect(residualSeries([], null)).toEqual([[], []])
  })
  it('bounds zoom at both ends without shrinking the intended window', () => {
    expect(resizeRange({ start: 0, end: 100 }, 0.5)).toEqual({ start: 25, end: 75 })
    expect(resizeRange({ start: 0, end: 25 }, 2)).toEqual({ start: 0, end: 50 })
    expect(resizeRange({ start: 75, end: 100 }, 2)).toEqual({ start: 50, end: 100 })
    expect(resizeRange({ start: 25, end: 75 }, 10)).toEqual({ start: 0, end: 100 })
  })
})
