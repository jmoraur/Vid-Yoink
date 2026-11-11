import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { Icon } from '../components/ui/Icon'
import { Skeleton } from '../components/ui/Skeleton'
import { fullDate, timeAgo } from '../lib/format'

export function Archive() {
  const [q, setQ] = useState('')
  const [params] = useSearchParams()
  const subFilter = params.get('sub') ? Number(params.get('sub')) : undefined
  const queryClient = useQueryClient()
  const entries = useQuery({
    queryKey: ['archive', q, subFilter],
    queryFn: () => api.listArchive(q || undefined, subFilter),
  })
  const subs = useQuery({ queryKey: ['subscriptions'], queryFn: api.listSubscriptions })
  const subName = subs.data?.find((sub) => sub.id === subFilter)?.name
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteArchiveEntry(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['archive'] }),
  })

  return (
    <div>
      <p className="hint">
        Everything yoink has downloaded. It remembers the videos, not the files, so you can
        move or rename files freely. Remove an entry to let that video be downloaded again.
      </p>
      {subFilter != null && (
        <p className="hint">
          Only showing items from {subName ? `“${subName}”` : 'one subscription'}.{' '}
          <Link to="/subscriptions/archive">Show everything</Link>
        </p>
      )}
      <div className="page-actions">
        <div className="search-wrap">
          <Icon name="search" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by title or video ID…"
            aria-label="Search archive"
            className="search"
          />
        </div>
      </div>
      {entries.isPending && <Skeleton lines={3} />}
      {entries.isError && (
        <ErrorState message={entries.error.message} onRetry={() => entries.refetch()} />
      )}
      {entries.data && (
        <section className="jobs">
          {entries.data.map((e) => (
            <div className="job" key={e.id}>
              <div className="job-main">
                <span className="job-title">{e.title ?? `${e.extractor}: ${e.video_id}`}</span>
                <span className="job-actions">
                  <button
                    className="ghost-icon"
                    onClick={() => remove.mutate(e.id)}
                    aria-label="Forget this video"
                    title="Forget this video (it can then be downloaded again)"
                  >
                    <Icon name="trash" />
                  </button>
                </span>
              </div>
              <p className="job-facts">
                <span>{e.extractor}</span>
                <span className="font-mono">{e.video_id}</span>
                <time dateTime={e.created_at} title={fullDate(e.created_at)}>
                  added {timeAgo(e.created_at)}
                </time>
              </p>
            </div>
          ))}
          {entries.data.length === 0 && (
            <EmptyState
              icon="archive"
              title="Nothing downloaded yet"
              hint={q ? 'Nothing matches this search.' : 'Finished downloads are recorded here.'}
            />
          )}
        </section>
      )}
    </div>
  )
}
