import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Job, JobStatus } from '../api/types'
import { api } from '../api/client'
import { useCancelling, useJobProgress } from '../ws'
import { Icon } from './ui/Icon'

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

const CHIP: Record<JobStatus, string> = {
  queued: 'chip-muted',
  running: 'chip-accent',
  finished: 'chip-ok',
  error: 'chip-danger',
  cancelled: 'chip-warn',
}

export function JobRow({ job }: { job: Job }) {
  const live = useJobProgress(job.id)
  const cancelling = useCancelling(job.id)
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['downloads'] })
  const cancel = useMutation({ mutationFn: () => api.cancelDownload(job.id) })
  const retry = useMutation({
    mutationFn: () => api.retryDownload(job.id),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: () => api.deleteDownload(job.id),
    onSuccess: invalidate,
  })

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
          <span className="muted font-mono">
            {progress.playlist_index}/{progress.playlist_count}
          </span>
        )}
        <span className={`chip ${cancelling && active ? 'chip-warn' : CHIP[job.status]}`}>
          {shownStatus}
        </span>
        <span className="job-actions">
          {active && !cancelling && (
            <button
              className="ghost-icon"
              onClick={() => cancel.mutate()}
              aria-label="Cancel download"
              title="Cancel download"
            >
              <Icon name="x" />
            </button>
          )}
          {(job.status === 'error' || job.status === 'cancelled') && (
            <button
              className="ghost-icon"
              onClick={() => retry.mutate()}
              aria-label="Retry download"
              title="Retry download"
            >
              <Icon name="retry" />
            </button>
          )}
          {!active && (
            <button
              className="ghost-icon"
              onClick={() => remove.mutate()}
              aria-label="Delete from list"
              title="Delete from list"
            >
              <Icon name="trash" />
            </button>
          )}
        </span>
      </div>
      {job.status === 'running' && progress?.status === 'downloading' && (
        <div className="job-progress">
          <div
            className="bar"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={pct ?? undefined}
            aria-label="Download progress"
          >
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
