import type { components } from '../generated/api'
import { format } from '../lib/api'

type Diagnostic = components['schemas']['SatelliteDiagnostic']

export function SatelliteInspector({
  satellite,
  selectedId,
}: {
  satellite?: Diagnostic
  selectedId?: string
}) {
  return (
    <section className="satellite-inspector" aria-label="选中卫星详情">
      <div className="inspector-heading">
        <h3>{satellite?.sat_id ?? selectedId ?? '卫星详情'}</h3>
        {satellite && (
          <span className={satellite.excluded ? 'warning-text' : 'muted'}>
            {satellite.excluded ? '已剔除' : satellite.weight > 0 ? '参与定位' : '未参与定位'}
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
            <dt>最终 / 提议权重</dt>
            <dd>
              {format(satellite.weight, 0)} / {format(satellite.robust_weight, 3)}
            </dd>
          </div>
        </dl>
      ) : (
        <p className="inspector-empty">
          {selectedId
            ? '当前历元没有这颗卫星的诊断数据。'
            : '运行后，点击天空图或卫星行查看观测详情。'}
        </p>
      )}
    </section>
  )
}
