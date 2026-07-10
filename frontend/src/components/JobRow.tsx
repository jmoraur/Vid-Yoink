import { useMutation } from '@tanstack/react-query'
import type { Job } from '../api/types'
import { api } from '../api/client'
import { useCancelling, useJobProgress } from '../ws'

function formatBytes(n: number | null | undefined): string {
  if (n == null) return '—'
  const units = ['B', 'KiB', 'MiB', 'GiB']
  let i = 0
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i++
  }
  return `${n.toFixed(1)} ${units[i]}`
}

function formatEta(s: number | null | undefined): string {
  if (s == null) return '—'
  const m = Math.floor(s / 60)
  return m > 0 ? `${m}m${Math.round(s % 60)}s` : `${Math.round(s)}s`
}

export function JobRow({ job }: { job: Job }) {
  const live = useJobProgress(job.id)
  const cancelling = useCancelling(job.id)
  const cancel = useMutation({ mutationFn: () => api.cancelDownload(job.id) })

  const progress = live ?? job.progress ?? undefined
  const active = job.status === 'queued' || job.status === 'running'
  const pct = progress?.progress != null ? Math.round(progress.progress * 100) : null
  const shownStatus = cancelling && active ? 'cancelling…' : job.status
  const label =
    job.title ??
    progress?.item_title ??
    progress?.filename ??
    job.url

  return (
    <div className={`job job-${job.status}`}>
      <div className="job-main">
        <span className="job-title" title={job.url}>
          {label}
        </span>
        {progress?.playlist_index != null && progress?.playlist_count != null && (
          <span className="muted">
            {progress.playlist_index}/{progress.playlist_count}
          </span>
        )}
        <span className={`job-status status-${job.status}`}>{shownStatus}</span>
        {active && !cancelling && (
          <button className="small" onClick={() => cancel.mutate()}>
            Cancel
          </button>
        )}
      </div>
      {job.status === 'running' && progress?.status === 'downloading' && (
        <div className="job-progress">
          <div className="bar">
            <div className="fill" style={{ width: `${pct ?? 0}%` }} />
          </div>
          <span className="stats">
            {pct != null ? `${pct}%` : '…'} · {formatBytes(progress.speed)}/s · ETA{' '}
            {formatEta(progress.eta)}
          </span>
        </div>
      )}
      {job.status === 'running' && progress?.status === 'postprocessing' && (
        <p className="muted">Post-processing ({progress.postprocessor ?? '…'})</p>
      )}
      {job.error && <p className="error">{job.error}</p>}
      {job.status === 'finished' && job.files.length > 0 && (
        <p className="files" title={job.files.join('\n')}>
          {job.files.map((f) => f.split('/').pop()).join(', ')}
        </p>
      )}
    </div>
  )
}
