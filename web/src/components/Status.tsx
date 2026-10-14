import { statusLabels, statusTone } from '../lib/api'

export function Status({ value }: { value?: string }) {
  return (
    <span className={`status status-${statusTone(value)}`}>
      <span className="status-dot" />
      {value ? statusLabels[value] || value : '待运行'}
    </span>
  )
}
