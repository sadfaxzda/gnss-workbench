import type { components } from '../generated/api'

type Solution = components['schemas']['Solution']

export function adoptedCandidate(solution: Solution, raw: Record<string, unknown>): boolean {
  const excluded = [...(solution.excluded_sats ?? [])].sort()
  const ids = typeof raw.sat_id === 'string' ? raw.sat_id.split('+').sort() : []
  // Actual exclusions are authoritative, including older single-FDE logs that
  // did not write the optional selected field.
  return (
    excluded.length > 0 &&
    ids.length === excluded.length &&
    ids.every((id, i) => id === excluded[i])
  )
}

export function hypothesisEvidence(solution: Solution) {
  const row = solution.candidate_scores?.find((raw) => adoptedCandidate(solution, raw))
  if (!row) return null
  const method = typeof row.selection_method === 'string' ? row.selection_method : ''
  const source = method === 'provisional_likelihood' ? String(row.provisional_source ?? '') : method
  const labels: Record<string, string> = {
    current: '当前历元残差',
    current_likelihood: '当前历元残差',
    causal_likelihood: '历史残差证据',
    history: '历史残差证据',
    unconfirmed_history: '历史残差证据（未确认）',
    coherent_history: '历史偏差一致性',
    coherent_likelihood: '历史偏差一致性',
    coherent_proposal: '历史偏差提议（仅暂定）',
    unique_passing: '唯一通过子集（相对证据不足）',
    unique_subset: '唯一通过子集',
  }
  const finite = (value: unknown) =>
    typeof value === 'number' && Number.isFinite(value) ? value : null
  const currentOnly = source === 'current' || source === 'unique_passing'
  const currentShare = finite(row.current_likelihood_share)
  // Unresolved snapshots can retain a different historical winner's log ratio.
  // Never present that number as support for the actually adopted current fit.
  const currentLogRatio =
    currentShare !== null && currentShare > 0 && currentShare < 1
      ? Math.log(currentShare) - Math.log1p(-currentShare)
      : null
  return {
    satellites: (solution.excluded_sats ?? []).join('、'),
    provisional: solution.status === 'SUSPECT',
    source:
      labels[source] ?? (solution.algorithm === 'single_fde' ? '单星排除检验' : '旧记录未提供'),
    epochs: currentOnly || source === 'current_likelihood' ? 1 : finite(row.evidence_epochs),
    logRatio: currentOnly ? currentLogRatio : finite(row.selection_log_ratio),
    requiredLogRatio: finite(row.required_log_ratio),
    historySigma: finite(row.history_sigma_m),
  }
}
