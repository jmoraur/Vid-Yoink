import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'

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
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by title or video ID…"
          className="search"
        />
      </div>
      <section className="jobs">
        {entries.data?.map((e) => (
          <div className="job" key={e.id}>
            <div className="job-main">
              <span className="job-title">{e.title ?? `${e.extractor}: ${e.video_id}`}</span>
              <span className="muted">
                {e.extractor} · {e.video_id}
              </span>
              <button className="small" onClick={() => remove.mutate(e.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
        {entries.data?.length === 0 && <p className="muted">Archive is empty.</p>}
      </section>
    </div>
  )
}
