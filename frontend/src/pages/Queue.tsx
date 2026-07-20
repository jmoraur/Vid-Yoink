import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { JobStatus } from '../api/types'
import { JobRow } from '../components/JobRow'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { Skeleton } from '../components/ui/Skeleton'

const FILTERS: { label: string; value: JobStatus | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'running' },
  { label: 'Finished', value: 'finished' },
  { label: 'Errors', value: 'error' },
  { label: 'Cancelled', value: 'cancelled' },
]

export function Queue() {
  const [filter, setFilter] = useState<JobStatus | 'all'>('all')
  const jobs = useQuery({ queryKey: ['downloads'], queryFn: api.listDownloads })

  const visible = jobs.data?.filter((j) => {
    if (filter === 'all') return true
    if (filter === 'running') return j.status === 'running' || j.status === 'queued'
    return j.status === filter
  })

  return (
    <div>
      <div className="filters">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            className={`small ${filter === f.value ? 'active' : ''}`}
            aria-pressed={filter === f.value}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>
      {jobs.isPending && <Skeleton lines={3} />}
      {jobs.isError && <ErrorState message={jobs.error.message} onRetry={() => jobs.refetch()} />}
      {visible && (
        <section className="jobs">
          {visible.map((job) => <JobRow key={job.id} job={job} />)}
          {visible.length === 0 &&
            (filter === 'all' ? (
              <EmptyState
                icon="inbox"
                title="Queue is clear"
                hint="Paste a URL on the Download page to start."
              />
            ) : (
              <EmptyState icon="inbox" title="Nothing here" hint="No downloads match this filter." />
            ))}
        </section>
      )}
    </div>
  )
}
