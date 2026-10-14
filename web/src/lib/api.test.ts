import { describe, expect, it } from 'vitest'
import { format, upsertEpochs, statusTone, requestError, type EpochFrame } from './api'

describe('live telemetry handling', () => {
  it('identifies the invalid parameter rather than only displaying HTTP 422', () => {
    expect(
      requestError(
        [{ loc: ['body', 'tcp_port'], type: 'less_than_equal', ctx: { le: 65535 } }],
        422,
      ),
    ).toBe('TCP 端口不得大于 65535，请修改后重试')
    expect(requestError('文件中没有 epoch 观测帧', 422)).toBe('文件中没有 epoch 观测帧')
  })
  it('does not turn an unavailable coordinate into zero', () => {
    expect(format(null)).toBe('—')
    expect(format(0)).toBe('0.00')
    expect(statusTone('INVALID_INSUFFICIENT')).toBe('bad')
  })
  it('deduplicates replayed frames after reconnect without losing empty epochs', () => {
    const frame = (id: number) =>
      ({ epoch_id: id, improved: { status: 'NO_OBSERVATIONS' } }) as EpochFrame
    const merged = upsertEpochs([frame(2), frame(4)], [frame(4), frame(3)])
    expect(merged.map((e) => e.epoch_id)).toEqual([2, 4, 3])
    expect(merged[2].improved.status).toBe('NO_OBSERVATIONS')
  })
})
