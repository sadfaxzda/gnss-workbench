import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ChevronLeft, ChevronRight, History, RefreshCw, Search } from 'lucide-react'
import { Button } from './Button'
import { Status } from './Status'
import { type Dataset, type Run, requestRunHistory } from '../lib/api'
import { algorithmLabels } from '../lib/presentation'

const pageSize = 25

export function RunHistory({
  datasets,
  onOpen,
  onNew,
}: {
  datasets: Dataset[]
  onOpen: (run: Run) => void
  onNew: () => void
}) {
  const [offset, setOffset] = useState(0)
  const [query, setQuery] = useState('')
  const [draft, setDraft] = useState('')
  const { data, isPending, isFetching, error, refetch } = useQuery({
    queryKey: ['runs', 'history', offset, query],
    queryFn: () => requestRunHistory(offset, pageSize, query),
  })
  const runs = data?.items ?? []
  const total = data?.total ?? 0
  return (
    <section className="panel run-history">
      <div className="panel-heading">
        <div>
          <h2>实验运行记录</h2>
          <p>保存的输入、参数与解算结果</p>
        </div>
        <span className="count-badge">{data ? `共 ${total} 次运行` : '正在读取'}</span>
      </div>
      <form
        className="history-toolbar"
        onSubmit={(event) => {
          event.preventDefault()
          setOffset(0)
          setQuery(draft.trim())
        }}
      >
        <label>
          <Search size={14} />
          <input
            aria-label="检索运行记录"
            placeholder="运行编号 / 数据集编号"
            maxLength={100}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <Button variant="outline" type="submit">
          检索
        </Button>
        {query && (
          <button
            type="button"
            className="text-button"
            onClick={() => {
              setDraft('')
              setQuery('')
              setOffset(0)
            }}
          >
            清除检索
          </button>
        )}
        <button
          type="button"
          className="grid-command"
          disabled={isFetching}
          onClick={() => void refetch()}
        >
          <RefreshCw size={13} />
          刷新
        </button>
      </form>
      {error && (
        <div className="alert alert-error" role="alert">
          {error.message}
        </div>
      )}
      <div className="table-scroll" aria-busy={isFetching}>
        <table aria-label="历史运行表">
          <thead>
            <tr>
              <th>运行编号</th>
              <th>观测数据</th>
              <th>算法 / 输入</th>
              <th>创建时间</th>
              <th className="numeric">历元</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td className="mono">{run.id.slice(0, 8)}</td>
                <td className="history-dataset">
                  {datasets.find((dataset) => dataset.id === run.configuration.dataset_id)?.title ??
                    run.configuration.dataset_id}
                  <small className="table-sub">{run.configuration.dataset_id}</small>
                </td>
                <td>
                  {run.configuration.enable_fde
                    ? algorithmLabels[run.configuration.algorithm ?? 'consensus']
                    : '故障检测关闭'}
                  <small className="table-sub">
                    {run.configuration.source === 'tcp'
                      ? 'TCP 接入'
                      : run.configuration.scenario?.kind !== 'none'
                        ? '受控故障实验'
                        : '文件回放'}
                  </small>
                </td>
                <td>{new Date(run.created_at).toLocaleString('zh-CN', { hour12: false })}</td>
                <td className="numeric">{run.epoch_count}</td>
                <td>
                  <Status value={run.status} />
                </td>
                <td>
                  <Button variant="ghost" onClick={() => onOpen(run)}>
                    查看 <ArrowRight size={14} />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!runs.length && !error && (
          <div className="empty-state">
            <History size={25} />
            <strong>
              {isPending ? '正在读取运行记录…' : query ? '未找到匹配的运行' : '暂无运行记录'}
            </strong>
            {!isPending && !query && <Button onClick={onNew}>新建运行</Button>}
          </div>
        )}
      </div>
      <div className="history-pagination">
        <span>{total ? `${offset + 1}–${offset + runs.length} / ${total} 条` : '0 条记录'}</span>
        <div>
          <button
            className="icon-button"
            aria-label="上一页运行记录"
            disabled={offset === 0 || isFetching}
            onClick={() => setOffset(Math.max(0, offset - pageSize))}
          >
            <ChevronLeft size={14} />
          </button>
          <span>
            第 {Math.floor(offset / pageSize) + 1} / {Math.max(1, Math.ceil(total / pageSize))} 页
          </span>
          <button
            className="icon-button"
            aria-label="下一页运行记录"
            disabled={offset + pageSize >= total || isFetching}
            onClick={() => setOffset(offset + pageSize)}
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </section>
  )
}
