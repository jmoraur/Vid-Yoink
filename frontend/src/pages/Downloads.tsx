import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { DEFAULT_OPTIONS, type DownloadOptions, type Job } from '../api/types'
import { JobRow } from '../components/JobRow'
import { ProbeCard } from '../components/ProbeCard'
import { OptionsForm } from '../components/options/OptionsForm'
import { PresetBar } from '../components/options/PresetBar'
import { summarize } from '../components/options/summarize'
import { splitLinks } from '../lib/format'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { Icon } from '../components/ui/Icon'
import { Skeleton } from '../components/ui/Skeleton'
import { Spinner } from '../components/ui/Spinner'

function useDebounced(value: string, ms: number): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

const looksLikeUrl = (s: string) => /^https?:\/\/\S+\.\S+/.test(s)
const isActive = (job: Job) => job.status === 'queued' || job.status === 'running'

type Filter = 'all' | 'finished' | 'error' | 'cancelled'
const FILTERS: { label: string; value: Filter }[] = [
  { label: 'All', value: 'all' },
  { label: 'Finished', value: 'finished' },
  { label: 'Failed', value: 'error' },
  { label: 'Cancelled', value: 'cancelled' },
]
// What "Clear" removes under each filter. Under "All" it is the finished ones only:
// failed and cancelled rows are things you may still want to retry.
const CLEARS: Record<Filter, { status: Exclude<Filter, 'all'>; label: string }> = {
  all: { status: 'finished', label: 'Clear finished' },
  finished: { status: 'finished', label: 'Clear finished' },
  error: { status: 'error', label: 'Clear failed' },
  cancelled: { status: 'cancelled', label: 'Clear cancelled' },
}

export function Downloads() {
  const [url, setUrl] = useState('')
  const [options, setOptions] = useState<DownloadOptions>(DEFAULT_OPTIONS)
  const [showOptions, setShowOptions] = useState(false)
  const [filter, setFilter] = useState<Filter>('all')
  const queryClient = useQueryClient()
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['downloads'] })

  const links = splitLinks(url) // several links, one per line = one download each
  const typed = links.length === 1 ? links[0] : '' // only a single link gets a preview
  const probeUrl = useDebounced(typed, 700)
  const probe = useQuery({
    queryKey: ['probe', probeUrl],
    queryFn: () => api.probe(probeUrl),
    enabled: looksLikeUrl(probeUrl),
    staleTime: Infinity,
    retry: false,
  })
  const probeIsCurrent = typed !== '' && probeUrl === typed // not a leftover of the last URL

  const jobs = useQuery({ queryKey: ['downloads'], queryFn: api.listDownloads })
  const create = useMutation({
    mutationFn: async () => {
      const results = await Promise.allSettled(links.map((l) => api.createDownload(l, options)))
      // stay here: new jobs show up under "Now"; the options stay for the next link.
      // Links that were refused stay in the field, so pressing again cannot repeat the rest.
      setUrl(links.filter((_, i) => results[i].status === 'rejected').join('\n'))
      setOptions((o) => ({ ...o, playlist_items: null }))
      refresh()
      const refused = results.find((r) => r.status === 'rejected')
      if (refused) throw refused.reason
    },
  })
  const retryFailed = useMutation({ mutationFn: api.retryFailed, onSuccess: refresh })
  const clear = useMutation({
    mutationFn: () => api.clearDownloads(CLEARS[filter].status),
    onSuccess: refresh,
  })

  // the API lists newest first; "Now" reads top-down in the order things will happen
  const now = jobs.data?.filter(isActive).reverse() ?? []
  const earlier = jobs.data?.filter((j) => !isActive(j)) ?? []
  const shown = earlier.filter((j) => filter === 'all' || j.status === filter)
  const failedCount = earlier.filter((j) => j.status === 'error').length
  const clearable = earlier.some((j) => j.status === CLEARS[filter].status)

  return (
    <div>
      <form
        className="download-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (links.length) create.mutate()
        }}
      >
        <textarea
          rows={Math.min(8, url.split('\n').length)}
          value={url}
          onChange={(e) => {
            setUrl(e.target.value)
            setOptions((o) => ({ ...o, playlist_items: null })) // selection belongs to old URL
          }}
          onKeyDown={(e) => {
            // Enter sends, like in a one-line field; Shift+Enter starts another line
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault()
              e.currentTarget.form?.requestSubmit()
            }
          }}
          placeholder="Paste a video or playlist link, or several (one per line)…"
          aria-label="Video or playlist links, one per line"
          autoFocus
        />
        <button
          type="button"
          className={`ghost options-toggle ${showOptions ? 'active' : ''}`}
          aria-expanded={showOptions}
          aria-controls="download-options"
          aria-label="Download options"
          title="Download options"
          onClick={() => setShowOptions(!showOptions)}
        >
          <Icon name="sliders" size={18} />
        </button>
        <button type="submit" disabled={create.isPending || links.length === 0}>
          <Icon name="download" /> Download{links.length > 1 && ` ${links.length}`}
        </button>
      </form>
      {create.isError && <p className="error">{create.error.message}</p>}

      {showOptions ? (
        <div id="download-options" className="options-panel">
          <PresetBar options={options} onLoad={setOptions} />
          <OptionsForm
            value={options}
            onChange={setOptions}
            heights={probeIsCurrent ? probe.data?.heights : undefined}
          />
        </div>
      ) : (
        <p className="options-summary">
          {summarize(options)}
          {' · '}
          <button type="button" className="link" onClick={() => setShowOptions(true)}>
            Change
          </button>
        </p>
      )}

      {links.length > 1 && (
        <p className="hint">
          {links.length} links. Each one becomes its own download, with the options above.
        </p>
      )}
      {probeIsCurrent && probe.isFetching && <Spinner label="Looking up the link…" />}
      {probeIsCurrent && probe.isError && (
        <p className="error">Could not read this link: {probe.error.message}</p>
      )}
      {probeIsCurrent && probe.data && (
        <ProbeCard
          probe={probe.data}
          playlistItems={options.playlist_items}
          onPlaylistItems={(items) => setOptions({ ...options, playlist_items: items })}
        />
      )}

      {jobs.isPending && <Skeleton lines={3} />}
      {jobs.isError && <ErrorState message={jobs.error.message} onRetry={() => jobs.refetch()} />}

      {now.length > 0 && (
        <section className="job-list" aria-labelledby="now-heading">
          <div className="list-head">
            <h2 id="now-heading">Now</h2>
          </div>
          <div className="jobs">
            {now.map((job) => (
              <JobRow key={job.id} job={job} />
            ))}
          </div>
        </section>
      )}

      {earlier.length > 0 && (
        <section className="job-list" aria-labelledby="earlier-heading">
          <div className="list-head">
            <h2 id="earlier-heading">Earlier</h2>
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
            <div className="list-actions">
              {failedCount > 0 && (
                <button
                  className="small"
                  disabled={retryFailed.isPending}
                  onClick={() => retryFailed.mutate()}
                >
                  <Icon name="retry" size={14} /> Retry failed ({failedCount})
                </button>
              )}
              <button
                className="small"
                disabled={!clearable || clear.isPending}
                onClick={() => clear.mutate()}
                title="Removes the rows from this list. Files stay where they are."
              >
                {CLEARS[filter].label}
              </button>
            </div>
          </div>
          <div className="jobs">
            {shown.map((job) => (
              <JobRow key={job.id} job={job} />
            ))}
            {shown.length === 0 && (
              <EmptyState icon="inbox" title="Nothing here" hint="No downloads match this filter." />
            )}
          </div>
        </section>
      )}

      {jobs.data?.length === 0 && (
        <EmptyState
          icon="inbox"
          title="No downloads yet"
          hint="Paste a link above and press Download. Progress shows up right here."
        />
      )}
    </div>
  )
}
