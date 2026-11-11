import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Job } from '../api/types'
import { api } from '../api/client'
import { formatBytes, formatDuration, fullDate, hostOf, timeAgo } from '../lib/format'
import { useCancelling, useJobProgress } from '../ws'
import { Icon } from './ui/Icon'

const AUDIO = new Set(['mp3', 'm4a', 'opus', 'flac', 'wav', 'ogg', 'aac'])
const extension = (path: string) => path.split('.').pop()?.toLowerCase() ?? ''

/** Small 16:9 picture loaded straight from the site; an icon when there is none. */
function Thumb({ src, audio }: { src: string | null | undefined; audio: boolean }) {
  const [broken, setBroken] = useState(false)
  return (
    <div className="thumb">
      {src && !broken ? (
        <img
          src={src}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setBroken(true)}
        />
      ) : (
        <Icon name={audio ? 'music' : 'film'} size={20} />
      )}
    </div>
  )
}

type Tone = 'queued' | 'running' | 'finished' | 'error' | 'cancelled'

export function JobRow({ job }: { job: Job }) {
  const live = useJobProgress(job.id)
  const cancelling = useCancelling(job.id)
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['downloads'] })
  const cancel = useMutation({ mutationFn: () => api.cancelDownload(job.id) })
  const retry = useMutation({ mutationFn: () => api.retryDownload(job.id), onSuccess: invalidate })
  const remove = useMutation({ mutationFn: () => api.deleteDownload(job.id), onSuccess: invalidate })
  const openFolder = useMutation({ mutationFn: () => api.openFolder(job.id) })

  const progress = live ?? job.progress ?? undefined
  const active = job.status === 'queued' || job.status === 'running'
  const downloading = job.status === 'running' && progress?.status === 'downloading'
  const pct = progress?.progress != null ? Math.round(progress.progress * 100) : null
  const failedItems = job.error ? job.error.split('\n').length : 0
  const label = job.title ?? progress?.item_title ?? progress?.filename ?? job.url
  const when = job.finished_at ?? job.created_at

  // One word (or a few) for the state, and its colour.
  let state: [string, Tone]
  if (cancelling && active) state = ['Stopping…', 'cancelled']
  else if (job.status === 'queued') state = ['Waiting', 'queued']
  else if (job.status === 'running')
    state = [
      downloading ? 'Downloading' : progress?.status === 'postprocessing' ? 'Finishing up' : 'Starting',
      'running',
    ]
  else if (job.status === 'error') state = ['Failed', 'error']
  else if (job.status === 'cancelled') state = ['Cancelled', 'cancelled']
  else if (job.files.length === 0 && job.skipped > 0) state = ['Already downloaded', 'queued']
  else if (job.error) state = [`Finished, ${failedItems} failed`, 'cancelled']
  else state = ['Finished', 'finished']

  // The quiet line of facts after the state.
  const facts: string[] = []
  if (downloading) {
    if (progress.playlist_index != null && progress.playlist_count != null)
      facts.push(`item ${progress.playlist_index} of ${progress.playlist_count}`)
    facts.push(pct != null ? `${pct}%` : '…')
    if (progress.speed) facts.push(`${formatBytes(progress.speed)}/s`)
    if (progress.eta != null) facts.push(`${formatDuration(progress.eta)} left`)
  } else {
    if (job.files.length === 1) facts.push(extension(job.files[0]))
    if (job.files.length > 1) facts.push(`${job.files.length} files`)
    if (job.filesize) facts.push(formatBytes(job.filesize))
    if (job.files.length > 0 && job.skipped > 0) facts.push(`${job.skipped} already downloaded`)
    facts.push(job.site ?? hostOf(job.url))
  }

  return (
    <div className={`job media job-${job.status}`}>
      <Thumb
        key={job.thumbnail ?? progress?.thumbnail}
        src={job.thumbnail ?? progress?.thumbnail}
        audio={AUDIO.has(extension(job.files[0] ?? progress?.filename ?? ''))}
      />
      <div className="job-body">
        <div className="job-main">
          <span className="job-title" title={job.url}>
            {label}
          </span>
          <span className="job-actions">
            {job.files.length > 0 && (
              <button
                className="ghost-icon"
                onClick={() => openFolder.mutate()}
                aria-label="Open folder"
                title="Open folder"
              >
                <Icon name="folder" />
              </button>
            )}
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
                aria-label="Try again"
                title="Try again"
              >
                <Icon name="retry" />
              </button>
            )}
            {!active && (
              <button
                className="ghost-icon"
                onClick={() => remove.mutate()}
                aria-label="Remove from list"
                title="Remove from list (the file stays)"
              >
                <Icon name="trash" />
              </button>
            )}
          </span>
        </div>
        <p className="job-facts">
          <span className={`state status-${state[1]}`}>{state[0]}</span>
          {facts.map((fact) => (
            <span key={fact}>{fact}</span>
          ))}
          {!active && <time dateTime={when} title={fullDate(when)}>{timeAgo(when)}</time>}
        </p>
        {downloading && (
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
        )}
        {job.error && <p className="error">{job.error}</p>}
        {openFolder.isError && <p className="error">{openFolder.error.message}</p>}
      </div>
    </div>
  )
}
