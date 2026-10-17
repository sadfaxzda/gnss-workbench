import type { components } from '../generated/api'
import { format } from '../lib/api'
import { hypothesisEvidence } from '../lib/hypothesisEvidence'

export function HypothesisEvidence({ solution }: { solution: components['schemas']['Solution'] }) {
  const evidence = hypothesisEvidence(solution)
  if (!evidence) return null
  return (
    <details className="method-note" aria-label="本次选择证据">
      <summary>
        本次选择证据 · {evidence.provisional ? '暂定，身份未确认' : '已采用'} {evidence.satellites}
      </summary>
      <dl className="satellite-values">
        <div>
          <dt>证据来源</dt>
          <dd>{evidence.source}</dd>
        </div>
        <div>
          <dt>证据历元数</dt>
          <dd>{format(evidence.epochs, 0)}</dd>
        </div>
        <div>
          <dt>对数证据比 / 门槛</dt>
          <dd>
            {format(evidence.logRatio, 3)} / {format(evidence.requiredLogRatio, 3)}
          </dd>
        </div>
        <div>
          <dt>历史噪声尺度</dt>
          <dd>{format(evidence.historySigma, 2)} m</dd>
        </div>
      </dl>
      <p>
        证据比是候选模型之间的相对分数，不是故障正确概率。达到门槛仍须满足当前检验和确认条件；暂定剔除保持身份未确认。缺失的旧日志字段显示为“—”。
      </p>
    </details>
  )
}
