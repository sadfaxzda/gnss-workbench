import type { EpochFrame } from './api'

export type StatusSegment = {
  start: number
  end: number
  firstEpoch: number
  lastEpoch: number
  status: string
  excluded: string[]
  flagged: string[]
}

/** Received results only: no scenario schedule or future observations. */
export function statusSegments(epochs: EpochFrame[]): StatusSegment[] {
  const segments: StatusSegment[] = []
  let previousKey = ''
  epochs.forEach((epoch, index) => {
    const { status, excluded_sats, flagged_sats } = epoch.improved
    const excluded = [...(excluded_sats ?? [])].sort()
    const flagged = [...(flagged_sats ?? [])].sort()
    const key = JSON.stringify([status, excluded, flagged])
    const previous = segments.at(-1)
    if (previous && key === previousKey) {
      previous.end = index
      previous.lastEpoch = epoch.epoch_id
    } else {
      segments.push({
        start: index,
        end: index,
        firstEpoch: epoch.epoch_id,
        lastEpoch: epoch.epoch_id,
        status,
        excluded,
        flagged,
      })
    }
    previousKey = key
  })
  return segments
}
