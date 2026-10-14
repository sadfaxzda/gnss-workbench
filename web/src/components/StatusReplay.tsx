import { useMemo } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { type EpochFrame, statusLabels, statusTone } from '../lib/api'
import { statusSegments, type StatusSegment } from '../lib/segments'

function description(segment: StatusSegment) {
  const range =
    segment.firstEpoch === segment.lastEpoch
      ? `${segment.firstEpoch}`
      : `${segment.firstEpoch}–${segment.lastEpoch}`
  const satellites = segment.excluded.length ? segment.excluded : segment.flagged
  return `历元 ${range} · ${statusLabels[segment.status] ?? segment.status}${satellites.length ? ` · ${satellites.join(' / ')}` : ''}`
}

export function StatusReplay({
  epochs,
  selectedIndex,
  onSelect,
}: {
  epochs: EpochFrame[]
  selectedIndex: number | null
  onSelect: (index: number) => void
}) {
  const segments = useMemo(() => statusSegments(epochs), [epochs])
  if (!segments.length) return null
  const index = selectedIndex ?? epochs.length - 1
  const active = Math.max(
    0,
    segments.findIndex((s) => index >= s.start && index <= s.end),
  )
  return (
    <section className="status-replay" aria-label="定位状态回放">
      <div className="replay-toolbar">
        <label htmlFor="status-segment">状态回放</label>
        <select
          id="status-segment"
          aria-label="定位状态区段"
          value={active}
          onChange={(event) => onSelect(segments[Number(event.target.value)].start)}
        >
          {segments.map((segment, n) => (
            <option key={segment.start} value={n}>
              {description(segment)}
            </option>
          ))}
        </select>
        <div className="replay-actions">
          <button
            aria-label="上一区段"
            title="上一区段"
            disabled={active === 0}
            onClick={() => onSelect(segments[active - 1].start)}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            aria-label="下一区段"
            title="下一区段"
            disabled={active === segments.length - 1}
            onClick={() => onSelect(segments[active + 1].start)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
      <div className="replay-strip" aria-label="历元状态分布">
        {segments.map((segment, n) => (
          <button
            key={segment.start}
            title={description(segment)}
            aria-label={`跳转到${description(segment)}`}
            aria-pressed={n === active}
            onClick={() => onSelect(segment.start)}
            className={`segment segment-${statusTone(segment.status)}${n === active ? ' selected' : ''}`}
            style={{ flexGrow: segment.end - segment.start + 1 }}
          />
        ))}
      </div>
    </section>
  )
}
