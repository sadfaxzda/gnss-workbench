import type { EpochFrame } from './api'

export type ZoomRange = { start: number; end: number }
export const fullRange: ZoomRange = { start: 0, end: 100 }

export function resizeRange(range: ZoomRange, factor: number): ZoomRange {
  const span = Math.min(100, Math.max(1, (range.end - range.start) * factor))
  const start = Math.max(0, Math.min(100 - span, (range.start + range.end - span) / 2))
  return { start, end: start + span }
}

// Keep original epoch slots: unavailable results must break a line, not shift time.
export function residualSeries(epochs: EpochFrame[], satelliteId: string | null) {
  return (['baseline', 'improved'] as const).map((kind) =>
    epochs.map((epoch) => {
      const solution = epoch[kind]
      if (!satelliteId) return solution.residual_rms_m ?? null
      return (
        solution.diagnostics?.find((satellite) => satellite.sat_id === satelliteId)?.residual_m ??
        null
      )
    }),
  )
}
