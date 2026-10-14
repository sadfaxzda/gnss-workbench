import { describe, expect, it } from 'vitest'
import { equalAxisBounds } from './chartTheme'

describe('trajectory coordinate geometry', () => {
  it('keeps a metre the same length on both axes of a wide viewport', () => {
    const bounds = equalAxisBounds(
      [
        [-30, -100],
        [230, 200],
      ],
      900,
      240,
    )!
    expect((bounds.xMax - bounds.xMin) / 900).toBeCloseTo((bounds.yMax - bounds.yMin) / 240)
    expect(bounds.xMin).toBeLessThan(-30)
    expect(bounds.xMax).toBeGreaterThan(230)
    expect(bounds.yMin).toBeLessThan(-100)
    expect(bounds.yMax).toBeGreaterThan(200)
  })

  it('handles empty and single-point runs without a collapsed domain', () => {
    expect(equalAxisBounds([], 400, 300)).toBeNull()
    const bounds = equalAxisBounds([[0, 0]], 300, 400)!
    expect(bounds.xMax - bounds.xMin).toBeGreaterThan(0)
    expect(bounds.yMax - bounds.yMin).toBeGreaterThan(0)
  })
})
