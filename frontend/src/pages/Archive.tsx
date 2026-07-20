import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { Icon } from '../components/ui/Icon'
import { Skeleton } from '../components/ui/Skeleton'

export function Archive() {
  const [q, setQ] = useState('')
  const [params] = useSearchParams()
  const subFilter = params.get('sub') ? Number(params.get('sub')) : undefined
  const queryClient = useQueryClient()
  const entries = useQuery({
    queryKey: ['archive', q, subFilter],
    queryFn: () => api.listArchive(q || undefined, subFilter),
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteArchiveEntry(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['archive'] }),
  })

  return (
    <div>
      <p className="hint">
        Everything yoink has downloaded, tracked by video ID — moving the files elsewhere
        does not cause re-downloads. Delete an entry to make it downloadable again.
      </p>
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
                <span className="muted font-mono">
                  {e.extractor} · {e.video_id}
                </span>
                <span className="job-actions">
                  <button
                    className="ghost-icon"
                    onClick={() => remove.mutate(e.id)}
                    aria-label="Delete archive entry"
                    title="Delete archive entry (allows re-download)"
                  >
                    <Icon name="trash" />
                  </button>
                </span>
              </div>
            </div>
          ))}
          {entries.data.length === 0 && (
            <EmptyState
              icon="archive"
              title="Archive is empty"
              hint={q ? 'Nothing matches this search.' : 'Finished downloads are recorded here.'}
            />
          )}
        </section>
      )}
    </div>
  )
}
