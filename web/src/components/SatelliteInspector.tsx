import type { components } from '../generated/api'
import { format } from '../lib/api'

type Diagnostic = components['schemas']['SatelliteDiagnostic']

export function SatelliteInspector({
  satellite,
  selectedId,
  provisional = false,
}: {
  satellite?: Diagnostic
  selectedId?: string
  provisional?: boolean
}) {
  return (
    <section className="satellite-inspector" aria-label="选中卫星详情">
      <div className="inspector-heading">
        <h3>{satellite?.sat_id ?? selectedId ?? '卫星详情'}</h3>
        {satellite && (
          <span className={satellite.excluded ? 'warning-text' : 'muted'}>
            {satellite.excluded
              ? provisional
                ? '暂定剔除（待确认）'
                : '已剔除'
              : satellite.weight > 0
                ? '参与定位'
                : '未参与定位'}
          </span>
        )}
      </div>
      {satellite ? (
        <dl className="satellite-values">
          <div>
            <dt>伪距残差</dt>
            <dd>
              {format(satellite.residual_m, 3)} <small>m</small>
            </dd>
          </div>
          <div>
            <dt>高度角 / 方位角</dt>
            <dd>
              {format(satellite.elevation_deg, 1)}° / {format(satellite.azimuth_deg, 1)}°
            </dd>
          </div>
          <div>
            <dt>最终 / 候选权重</dt>
            <dd>
              {format(satellite.weight, 0)} / {format(satellite.robust_weight, 3)}
            </dd>
          </div>
        </dl>
      ) : (
        <p className="inspector-empty">{selectedId ? '本历元无该卫星观测' : '选择卫星查看详情'}</p>
      )}
    </section>
  )
}
