import { describe, expect, it } from 'vitest'
import type { EpochFrame } from './api'
import { statusSegments } from './segments'

function frame(epoch_id: number, status: string, excluded_sats: string[] = []): EpochFrame {
  return {
    epoch_id,
    improved: { status, excluded_sats, flagged_sats: [] },
  } as unknown as EpochFrame
}

describe('status replay uses actual received decisions', () => {
  it('keeps missing observations and a recovery as separate sections', () => {
    const segments = statusSegments([
      frame(10, 'VALID'),
      frame(11, 'VALID'),
      frame(14, 'NO_OBSERVATIONS'),
      frame(15, 'INVALID_INSUFFICIENT'),
      frame(17, 'VALID'),
    ])
    expect(segments.map((s) => [s.start, s.end, s.firstEpoch, s.lastEpoch, s.status])).toEqual([
      [0, 1, 10, 11, 'VALID'],
      [2, 2, 14, 14, 'NO_OBSERVATIONS'],
      [3, 3, 15, 15, 'INVALID_INSUFFICIENT'],
      [4, 4, 17, 17, 'VALID'],
    ])
  })
  it('groups equal satellite sets but exposes a changed fault hypothesis', () => {
    const segments = statusSegments([
      frame(0, 'FAULT_EXCLUDED', ['G03', 'G20']),
      frame(1, 'FAULT_EXCLUDED', ['G20', 'G03']),
      frame(2, 'FAULT_EXCLUDED', ['G19']),
    ])
    expect(segments).toHaveLength(2)
    expect(segments[0]).toMatchObject({ start: 0, end: 1, excluded: ['G03', 'G20'] })
  })
  it('has no invented events for empty input', () => {
    expect(statusSegments([])).toEqual([])
  })
})
