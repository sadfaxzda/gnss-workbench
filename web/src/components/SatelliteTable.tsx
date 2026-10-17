import { useState } from 'react'
import type { components } from '../generated/api'
import { format } from '../lib/api'
import { DataGrid, type GridColumn } from './DataGrid'

type Satellite = components['schemas']['SatelliteDiagnostic'] & { provisional?: boolean }
const disposition = (sat: Satellite) =>
  sat.excluded
    ? sat.provisional
      ? '暂定剔除'
      : '异常剔除'
    : sat.weight > 0
      ? '参与定位'
      : '未参与定位'
const columns: GridColumn<Satellite>[] = [
  { id: 'satellite', label: '卫星', width: 86, value: (s) => s.sat_id },
  {
    id: 'elevation',
    label: '高度角 / °',
    width: 112,
    numeric: true,
    value: (s) => s.elevation_deg,
    render: (s) => format(s.elevation_deg, 1),
  },
  {
    id: 'azimuth',
    label: '方位角 / °',
    width: 112,
    numeric: true,
    value: (s) => s.azimuth_deg,
    render: (s) => format(s.azimuth_deg, 1),
  },
  {
    id: 'residual',
    label: '残差 / m',
    width: 126,
    numeric: true,
    value: (s) => s.residual_m,
    render: (s) => format(s.residual_m, 3),
  },
  {
    id: 'weight',
    label: '最终权重',
    width: 110,
    numeric: true,
    value: (s) => s.weight,
    render: (s) => format(s.weight, 3),
  },
  {
    id: 'robust',
    label: '候选权重',
    width: 110,
    numeric: true,
    value: (s) => s.robust_weight,
    render: (s) => format(s.robust_weight, 3),
  },
  {
    id: 'disposition',
    label: '处置',
    width: 130,
    value: disposition,
    render: (s) => <span className={s.excluded ? 'warning-text' : ''}>{disposition(s)}</span>,
  },
]
export function SatelliteTable({
  satellites,
  selectedId,
  onSelect,
  provisional = false,
}: {
  satellites: Satellite[]
  selectedId?: string
  onSelect: (id: string) => void
  provisional?: boolean
}) {
  const [filter, setFilter] = useState('all')
  const rows = satellites
    .map((sat) => ({ ...sat, provisional }))
    .filter(
      (sat) =>
        filter === 'all' ||
        (filter === 'excluded' ? sat.excluded : !sat.excluded && sat.weight > 0),
    )
  return (
    <DataGrid
      rows={rows}
      columns={columns}
      getId={(s) => s.sat_id}
      selectedId={selectedId}
      onSelect={onSelect}
      label="卫星观测表"
      totalRows={satellites.length}
      empty={satellites.length ? '无符合条件的观测' : '本历元无逐星诊断数据'}
      tools={
        <label>
          显示{' '}
          <select
            aria-label="卫星观测筛选"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          >
            <option value="all">全部观测</option>
            <option value="used">参与定位</option>
            <option value="excluded">已剔除观测</option>
          </select>
        </label>
      }
    />
  )
}
