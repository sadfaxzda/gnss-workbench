import { chartColors } from '../lib/chartTheme'
import type { components } from '../generated/api'

type Satellite = components['schemas']['SatelliteDiagnostic']

export function Skyplot({
  satellites,
  selectedId,
  onSelect,
}: {
  satellites: Satellite[]
  selectedId?: string
  onSelect?: (id: string) => void
}) {
  return (
    <svg
      className="skyplot"
      viewBox="0 0 340 340"
      role={onSelect ? 'group' : 'img'}
      aria-label="卫星天空图：方位角与高度角"
    >
      {[45, 90, 135].map((radius) => (
        <circle key={radius} cx="170" cy="170" r={radius} fill="none" stroke={chartColors.muted} />
      ))}
      <path d="M35 170H305 M170 35V305" stroke={chartColors.muted} />
      <g fill={chartColors.text} fontSize="12" textAnchor="middle">
        <text x="170" y="20">
          北 N
        </text>
        <text x="320" y="174">
          东
        </text>
        <text x="170" y="331">
          南
        </text>
        <text x="18" y="174">
          西
        </text>
      </g>
      {satellites.map((satellite) => {
        const radius = ((90 - Math.max(0, Math.min(90, satellite.elevation_deg))) / 90) * 135
        const angle = (satellite.azimuth_deg * Math.PI) / 180
        const x = 170 + radius * Math.sin(angle),
          y = 170 - radius * Math.cos(angle)
        return (
          <g
            key={satellite.sat_id}
            role={onSelect ? 'button' : undefined}
            tabIndex={onSelect ? 0 : undefined}
            aria-label={onSelect ? `选择卫星 ${satellite.sat_id}` : undefined}
            aria-pressed={onSelect ? selectedId === satellite.sat_id : undefined}
            onClick={() => onSelect?.(satellite.sat_id)}
            onKeyDown={(event) => {
              if (onSelect && (event.key === 'Enter' || event.key === ' ')) {
                event.preventDefault()
                onSelect(satellite.sat_id)
              }
            }}
            className={onSelect ? 'sky-satellite' : undefined}
          >
            <title>
              {satellite.sat_id}：高度角 {satellite.elevation_deg.toFixed(1)}°，残差{' '}
              {satellite.residual_m.toFixed(2)} m
            </title>
            <circle
              cx={x}
              cy={y}
              r="17"
              fill="transparent"
              stroke={selectedId === satellite.sat_id ? chartColors.improved : 'transparent'}
            />
            <circle
              cx={x}
              cy={y}
              r="8"
              fill={satellite.excluded ? chartColors.rejected : chartColors.satellite}
            />
            <text x={x} y={y - 13} textAnchor="middle" fontSize="12" fill={chartColors.text}>
              {satellite.sat_id}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
