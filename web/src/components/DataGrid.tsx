import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ArrowDown, ArrowUp, Copy } from 'lucide-react'

export type GridColumn<T> = {
  id: string
  label: string
  width: number
  numeric?: boolean
  value: (row: T) => number | string | null | undefined
  render?: (row: T) => ReactNode
}

export function DataGrid<T>({
  rows,
  columns,
  getId,
  selectedId,
  onSelect,
  label,
  empty,
  tools,
  totalRows,
}: {
  rows: T[]
  columns: GridColumn<T>[]
  getId: (row: T) => string
  selectedId?: string
  onSelect: (id: string) => void
  label: string
  empty: string
  tools?: ReactNode
  totalRows?: number
}) {
  const [sort, setSort] = useState({ id: columns[0].id, ascending: true })
  const [widths, setWidths] = useState<Record<string, number>>({})
  const [copyState, setCopyState] = useState('')
  const drag = useRef<{ id: string; x: number; width: number } | null>(null)
  const table = useRef<HTMLTableElement>(null)
  const sorted = useMemo(() => {
    const column = columns.find((column) => column.id === sort.id)
    if (!column) return rows
    return [...rows].sort((a, b) => {
      const left = column.value(a),
        right = column.value(b)
      if (left == null) return right == null ? 0 : 1
      if (right == null) return -1
      const difference =
        typeof left === 'number' && typeof right === 'number'
          ? left - right
          : String(left).localeCompare(String(right), 'zh-CN', { numeric: true })
      return sort.ascending ? difference : -difference
    })
  }, [rows, columns, sort])
  // Keep linked selections visible without scrolling the entire workspace.
  useEffect(() => {
    const index = sorted.findIndex((row) => getId(row) === selectedId)
    const row = table.current?.tBodies[0]?.rows[index]
    const viewport = table.current?.parentElement
    if (!row || !viewport) return
    const frame = viewport.getBoundingClientRect()
    const bounds = row.getBoundingClientRect()
    const headerHeight = table.current?.tHead?.getBoundingClientRect().height ?? 0
    if (bounds.top < frame.top + headerHeight)
      viewport.scrollTop += bounds.top - frame.top - headerHeight
    else if (bounds.bottom > frame.bottom) viewport.scrollTop += bounds.bottom - frame.bottom
  }, [selectedId, sorted, getId])
  const selected = rows.find((row) => getId(row) === selectedId)
  const width = (column: GridColumn<T>) => widths[column.id] ?? column.width
  function resize(id: string, value: number) {
    setWidths((current) => ({ ...current, [id]: Math.max(64, Math.min(420, value)) }))
  }
  async function copySelection() {
    if (!selected) return
    try {
      await navigator.clipboard.writeText(
        [
          columns.map((column) => column.label).join('\t'),
          columns.map((column) => column.value(selected) ?? '').join('\t'),
        ].join('\n'),
      )
      setCopyState(`已复制 ${getId(selected)}`)
    } catch {
      setCopyState('复制未完成，可选中单元格文字复制')
    }
  }
  return (
    <div className="data-grid">
      <div className="grid-toolbar">
        <div className="grid-tools">{tools}</div>
        <button className="grid-command" disabled={!selected} onClick={copySelection}>
          <Copy size={13} />
          复制选中行
        </button>
      </div>
      <div className="table-scroll grid-scroll">
        <table
          ref={table}
          className="engineering-grid"
          aria-label={label}
          style={{ width: columns.reduce((sum, col) => sum + width(col), 36) }}
          onKeyDown={(event) => {
            if (
              !['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key) ||
              !(event.target instanceof HTMLElement) ||
              !event.target.closest('tbody')
            )
              return
            if (!sorted.length) return
            event.preventDefault()
            const current = sorted.findIndex((row) => getId(row) === selectedId)
            const next =
              event.key === 'Home'
                ? 0
                : event.key === 'End'
                  ? sorted.length - 1
                  : Math.max(
                      0,
                      Math.min(sorted.length - 1, current + (event.key === 'ArrowUp' ? -1 : 1)),
                    )
            onSelect(getId(sorted[next]))
            const button =
              table.current?.querySelectorAll<HTMLButtonElement>('[data-row-select]')[next]
            button?.focus({ preventScroll: true })
            button?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
          }}
        >
          <colgroup>
            <col style={{ width: 36 }} />
            {columns.map((column) => (
              <col key={column.id} style={{ width: width(column) }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              <th className="grid-row-number" scope="col">
                #
              </th>
              {columns.map((column) => (
                <th
                  key={column.id}
                  scope="col"
                  className={column.numeric ? 'numeric' : ''}
                  aria-sort={
                    sort.id === column.id ? (sort.ascending ? 'ascending' : 'descending') : 'none'
                  }
                >
                  <button
                    className="grid-sort"
                    aria-label={`按${column.label}排序`}
                    onClick={() =>
                      setSort({
                        id: column.id,
                        ascending: sort.id === column.id ? !sort.ascending : true,
                      })
                    }
                  >
                    {column.label}
                    {sort.id === column.id ? (
                      sort.ascending ? (
                        <ArrowUp size={11} />
                      ) : (
                        <ArrowDown size={11} />
                      )
                    ) : (
                      <span className="sort-space" />
                    )}
                  </button>
                  <span
                    className="column-resizer"
                    role="separator"
                    aria-orientation="vertical"
                    aria-label={`调整${column.label}列宽`}
                    aria-valuenow={width(column)}
                    aria-valuemin={64}
                    aria-valuemax={420}
                    tabIndex={0}
                    onPointerDown={(event) => {
                      event.preventDefault()
                      event.currentTarget.setPointerCapture(event.pointerId)
                      drag.current = { id: column.id, x: event.clientX, width: width(column) }
                    }}
                    onPointerMove={(event) => {
                      if (drag.current?.id === column.id)
                        resize(column.id, drag.current.width + event.clientX - drag.current.x)
                    }}
                    onPointerUp={() => {
                      drag.current = null
                    }}
                    onPointerCancel={() => {
                      drag.current = null
                    }}
                    onDoubleClick={() => resize(column.id, column.width)}
                    onKeyDown={(event) => {
                      if (['ArrowLeft', 'ArrowRight', 'Home'].includes(event.key)) {
                        event.preventDefault()
                        event.stopPropagation()
                        resize(
                          column.id,
                          event.key === 'Home'
                            ? column.width
                            : width(column) + (event.key === 'ArrowLeft' ? -16 : 16),
                        )
                      }
                    }}
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, index) => (
              <tr
                key={getId(row)}
                className={getId(row) === selectedId ? 'selected-row' : ''}
                onClick={() => onSelect(getId(row))}
              >
                <th scope="row" className="grid-row-number">
                  {index + 1}
                </th>
                {columns.map((column, columnIndex) => (
                  <td key={column.id} className={column.numeric ? 'numeric' : ''}>
                    {columnIndex === 0 ? (
                      <button
                        data-row-select
                        className="satellite-select"
                        aria-label={`查看卫星 ${getId(row)}`}
                        aria-pressed={getId(row) === selectedId}
                        onClick={() => onSelect(getId(row))}
                      >
                        {column.render?.(row) ?? column.value(row) ?? '—'}
                      </button>
                    ) : (
                      (column.render?.(row) ?? column.value(row) ?? '—')
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <div className="grid-empty">{empty}</div>}
      </div>
      <div className="grid-status">
        <span>
          {rows.length === totalRows || totalRows == null
            ? `${rows.length} 条记录`
            : `显示 ${rows.length} / ${totalRows} 条`}
        </span>
        <span>已选择 {selected ? 1 : 0} 条</span>
        <span>只读</span>
        <span role="status">{copyState}</span>
      </div>
    </div>
  )
}
