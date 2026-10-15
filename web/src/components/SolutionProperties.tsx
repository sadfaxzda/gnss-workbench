import { type EpochFrame, type Evaluation, format } from '../lib/api'

function Property({
  label,
  value,
  unit,
  note,
}: {
  label: string
  value: string
  unit?: string
  note?: string
}) {
  return (
    <div title={note}>
      <dt>{label}</dt>
      <dd>
        <span>{value}</span>
        <small>{unit}</small>
      </dd>
    </div>
  )
}

export function SolutionProperties({
  epoch,
  stale,
  evaluation,
}: {
  epoch?: EpochFrame
  stale: boolean
  evaluation?: Evaluation
}) {
  const solution = epoch?.improved
  const availability = evaluation?.improved.availability_on_required
  const currentValues = stale ? 'position-details stale' : 'position-details'

  return (
    <div className="solution-properties">
      <section aria-label="当前历元解算质量">
        <h3 className="property-group-heading">
          解算质量 <span>改进解</span>
        </h3>
        <dl className={currentValues}>
          <Property
            label="参与解算卫星"
            value={solution ? String(solution.n_used) : '—'}
            unit="颗"
          />
          <Property
            label="PDOP"
            value={format(solution?.pdop)}
            note="位置精度因子 · 未加权卫星几何"
          />
          <Property
            label="残差 RMS"
            value={format(solution?.residual_rms_m, 3)}
            unit="m"
            note="参与解算观测的后验残差"
          />
        </dl>
      </section>
      <section aria-label="当前历元位置">
        <h3 className="property-group-heading">
          位置坐标 <span>WGS 84</span>
        </h3>
        <dl className={currentValues}>
          <Property label="纬度" value={format(epoch?.view.latitude_deg, 7)} unit="°" />
          <Property label="经度" value={format(epoch?.view.longitude_deg, 7)} unit="°" />
          <Property label="椭球高" value={format(epoch?.view.height_m, 3)} unit="m" />
        </dl>
      </section>
      <details className="property-disclosure">
        <summary>更多解算参数</summary>
        <dl className={currentValues}>
          <Property label="接收机钟差" value={format(solution?.clock_bias_m, 3)} unit="m" />
          <Property label="三维解差" value={format(epoch?.view.correction_m, 3)} unit="m" />
          <Property label="单历元计算" value={format(solution?.processing_ms, 2)} unit="ms" />
        </dl>
      </details>
      <details className="property-disclosure run-statistics">
        <summary>
          运行统计 <span>{evaluation ? '仿真 · 全程' : '暂无评价'}</span>
        </summary>
        <dl className="position-details" aria-label="全程仿真评价">
          <Property label="水平误差 P95" value={format(evaluation?.improved.h_p95_m)} unit="m" />
          <Property
            label="有效解比例"
            value={format(availability == null ? undefined : availability * 100)}
            unit="%"
          />
        </dl>
      </details>
    </div>
  )
}
