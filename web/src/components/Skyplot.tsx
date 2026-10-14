import type { components } from '../generated/api'

type Satellite = components['schemas']['SatelliteDiagnostic']

export function Skyplot({ satellites }: { satellites: Satellite[] }) {
  return (
    <svg
      className="skyplot"
      viewBox="0 0 340 340"
      role="img"
      aria-label="卫星天空图：方位角与高度角"
    >
      {[45, 90, 135].map((radius) => (
        <circle key={radius} cx="170" cy="170" r={radius} fill="none" stroke="#dce5eb" />
      ))}
      <path d="M35 170H305 M170 35V305" stroke="#dce5eb" />
      <g fill="#758190" fontSize="12" textAnchor="middle">
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
          <g key={satellite.sat_id}>
            <title>
              {satellite.sat_id}：高度角 {satellite.elevation_deg.toFixed(1)}°，残差{' '}
              {satellite.residual_m.toFixed(2)} m
            </title>
            <circle cx={x} cy={y} r="8" fill={satellite.excluded ? '#ce654a' : '#159d8d'} />
            <text x={x} y={y - 13} textAnchor="middle" fontSize="12" fill="#384b60">
              {satellite.sat_id}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
