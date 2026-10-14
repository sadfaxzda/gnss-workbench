import { describe, expect, it } from 'vitest'
import { format, upsertEpochs, statusTone, type EpochFrame } from './api'

describe('live telemetry handling', () => {
  it('does not turn an unavailable coordinate into zero', () => {
    expect(format(null)).toBe('—')
    expect(format(0)).toBe('0.00')
    expect(statusTone('INVALID_INSUFFICIENT')).toBe('bad')
  })
  it('deduplicates replayed frames after reconnect without losing empty epochs', () => {
    const frame = (id: number) =>
      ({ epoch_id: id, improved: { status: 'NO_OBSERVATIONS' } }) as EpochFrame
    const merged = upsertEpochs([frame(2), frame(4)], [frame(4), frame(3)])
    expect(merged.map((e) => e.epoch_id)).toEqual([2, 3, 4])
    expect(merged[2].improved.status).toBe('NO_OBSERVATIONS')
  })
})
