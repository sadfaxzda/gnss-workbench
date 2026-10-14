import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { type EpochFrame, type Run, upsertEpochs } from '../lib/api'

export function useRunStream(runId: string | null) {
  const [epochs, setEpochs] = useState<EpochFrame[]>([])
  const [run, setRun] = useState<Run | null>(null)
  const [connection, setConnection] = useState('idle')
  const [transport, setTransport] = useState('')
  const [positionStale, setPositionStale] = useState(false)
  const [error, setError] = useState('')
  const queryClient = useQueryClient()

  useEffect(() => {
    setEpochs([])
    setRun(null)
    setTransport('')
    setPositionStale(false)
    setError('')
    if (!runId) {
      setConnection('idle')
      return
    }
    let disposed = false
    let completed = false
    let socket: WebSocket | undefined
    let timer: ReturnType<typeof setTimeout> | undefined
    let attempts = 0
    const connect = () => {
      if (disposed) return
      setConnection('connecting')
      socket = new WebSocket(
        `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/runs/${runId}/stream`,
      )
      socket.onopen = () => {
        attempts = 0
        setConnection('connected')
        setError('')
      }
      socket.onmessage = ({ data }) => {
        try {
          const event = JSON.parse(data)
          if (event.schema !== 'gnss-stream/1') throw new Error('实时接口版本不兼容')
          if (event.type === 'snapshot') {
            setEpochs(event.epochs)
            setRun(event.run)
            setTransport(event.transport || '')
            setPositionStale(Boolean(event.position_stale))
            completed = !['running', 'stopping'].includes(event.run.status)
          } else if (event.type === 'epoch') {
            setPositionStale(false)
            setEpochs((previous) => upsertEpochs(previous, [event as EpochFrame]))
          } else if (event.type === 'transport') {
            setTransport(event.status)
            if (event.status === 'TRANSPORT_STALE') setPositionStale(true)
          } else if (event.type === 'heartbeat' || event.type === 'run_status') {
            setRun(event.run)
            completed = !['running', 'stopping'].includes(event.run.status)
            if (completed) {
              setConnection('completed')
              void queryClient.invalidateQueries({ queryKey: ['runs'] })
            }
          } else if (event.type === 'resync_required') {
            socket?.close()
          }
        } catch (e) {
          setError(e instanceof Error ? e.message : '实时数据读取失败')
        }
      }
      socket.onclose = ({ code }) => {
        if (disposed) return
        if (code === 1008) {
          setConnection('disconnected')
          setError('运行记录不可用，请在运行记录中重新选择或新建运行')
          return
        }
        if (completed) {
          setConnection('completed')
          return
        }
        setConnection('disconnected')
        attempts += 1
        timer = setTimeout(connect, Math.min(1000 * 2 ** Math.min(attempts - 1, 4), 10000))
      }
      socket.onerror = () => setError('连接中断，正在重连')
    }
    connect()
    return () => {
      disposed = true
      if (timer) clearTimeout(timer)
      socket?.close()
    }
  }, [runId, queryClient])
  return { epochs, run, connection, transport, positionStale, error }
}
