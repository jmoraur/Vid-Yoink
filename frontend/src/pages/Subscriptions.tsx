import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { api } from '../api/client'
import type { Subscription, SubscriptionIn } from '../api/types'
import { ConfirmDelete } from '../components/ui/ConfirmDelete'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { Icon } from '../components/ui/Icon'
import { Skeleton } from '../components/ui/Skeleton'
import { explain } from '../lib/errors'
import { formatInterval, fullDate, timeAgo } from '../lib/format'
import { Archive } from './Archive'

const EMPTY: SubscriptionIn = {
  name: '',
  url: '',
  preset_id: null,
  enabled: true,
  check_interval_minutes: null,
}

function SubscriptionEditor({
  sub,
  onDone,
}: {
  sub: Subscription | null // null = creating
  onDone: () => void
}) {
  const [form, setForm] = useState<SubscriptionIn>(sub ?? EMPTY)
  const [seedExisting, setSeedExisting] = useState(sub === null)
  const queryClient = useQueryClient()
  const presets = useQuery({ queryKey: ['presets'], queryFn: api.listPresets })
  const save = useMutation({
    mutationFn: async () => {
      if (sub) return api.updateSubscription(sub.id, form)
      const created = await api.createSubscription(form)
      if (seedExisting) await api.seedSubscription(created.id)
      return created
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      onDone()
    },
  })

  return (
    <div className="preset-editor">
      <div className="row">
        <label className="grow">
          Name
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            autoFocus
          />
        </label>
      </div>
      <div className="row">
        <label className="grow">
          Playlist / channel URL
          <input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
        </label>
      </div>
      <div className="row">
        <label>
          Preset
          <select
            value={form.preset_id ?? ''}
            onChange={(e) =>
              setForm({ ...form, preset_id: e.target.value === '' ? null : Number(e.target.value) })
            }
          >
            <option value="">Default options</option>
            {presets.data?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Check every (minutes)
          <input
            type="number"
            min={5}
            value={form.check_interval_minutes ?? ''}
            onChange={(e) =>
              setForm({
                ...form,
                check_interval_minutes: e.target.value === '' ? null : Number(e.target.value),
              })
            }
            placeholder="by hand only"
          />
        </label>
      </div>
      <div className="row checks">
        <label>
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
          />
          Enabled
        </label>
        {sub === null && (
          <label title="Add everything currently in the playlist to the archive without downloading">
            <input
              type="checkbox"
              checked={seedExisting}
              onChange={(e) => setSeedExisting(e.target.checked)}
            />
            Mark existing items as already downloaded
          </label>
        )}
      </div>
      <div className="row actions">
        <button
          disabled={!form.name.trim() || !form.url.trim() || save.isPending}
          onClick={() => save.mutate()}
        >
          {save.isPending ? 'Saving…' : sub ? 'Save changes' : 'Add subscription'}
        </button>
        <button className="small" onClick={onDone}>
          Cancel
        </button>
        {save.isError && <span className="error">{save.error.message}</span>}
      </div>
    </div>
  )
}

function SubscriptionRow({ sub }: { sub: Subscription }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
  const check = useMutation({ mutationFn: () => api.checkSubscription(sub.id), onSuccess: invalidate })
  const remove = useMutation({ mutationFn: () => api.deleteSubscription(sub.id), onSuccess: invalidate })

  if (editing) return <SubscriptionEditor sub={sub} onDone={() => setEditing(false)} />

  // "error: …" is how the server records a check that could not read the list
  const lastError = sub.last_check_result?.startsWith('error: ')
    ? sub.last_check_result.slice('error: '.length)
    : (check.data?.error ?? null)
  const schedule = !sub.enabled
    ? 'Paused'
    : sub.check_interval_minutes
      ? `Checks ${formatInterval(sub.check_interval_minutes)}`
      : 'Checked by hand only'

  return (
    <div className={`job ${sub.enabled ? '' : 'disabled'}`}>
      <div className="job-main">
        <span className="job-title" title={sub.url}>
          {sub.name}
        </span>
        <span className="job-actions">
          <button className="small" disabled={check.isPending} onClick={() => check.mutate()}>
            {check.isPending ? 'Checking…' : 'Check now'}
          </button>
          <button className="small" onClick={() => setEditing(true)}>
            Edit
          </button>
          <ConfirmDelete what={`subscription ${sub.name}`} onConfirm={() => remove.mutate()} />
        </span>
      </div>
      <p className="job-facts">
        <span>{schedule}</span>
        {sub.last_check_at ? (
          <span title={fullDate(sub.last_check_at)}>last checked {timeAgo(sub.last_check_at)}</span>
        ) : (
          <span>never checked</span>
        )}
        {sub.last_check_at && (
          <span>{lastError ? 'the check failed' : sub.last_check_result}</span>
        )}
        {sub.enabled && sub.next_check_at && (
          <span title={fullDate(sub.next_check_at)}>next check {timeAgo(sub.next_check_at)}</span>
        )}
        <span>
          <Link to={`/subscriptions/archive?sub=${sub.id}`}>downloaded items</Link>
        </span>
      </p>
      {lastError && (
        <div className="problem">
          <p>{explain(lastError)}</p>
          <details>
            <summary>Details</summary>
            <pre>{lastError}</pre>
          </details>
        </div>
      )}
    </div>
  )
}

export function Subscriptions() {
  return (
    <div>
      <div className="filters" role="navigation" aria-label="Subscription views">
        <NavLink to="/subscriptions" end className="tab">
          Subscriptions
        </NavLink>
        <NavLink to="/subscriptions/archive" className="tab">
          Downloaded items
        </NavLink>
      </div>
      <Routes>
        <Route index element={<SubscriptionList />} />
        <Route path="archive" element={<Archive />} />
      </Routes>
    </div>
  )
}

function SubscriptionList() {
  const [adding, setAdding] = useState(false)
  const subs = useQuery({ queryKey: ['subscriptions'], queryFn: api.listSubscriptions })

  return (
    <div>
      {adding ? (
        <SubscriptionEditor sub={null} onDone={() => setAdding(false)} />
      ) : (
        <div className="page-actions">
          <button onClick={() => setAdding(true)}>
            <Icon name="plus" /> Add subscription
          </button>
        </div>
      )}
      {subs.isPending && <Skeleton lines={2} />}
      {subs.isError && <ErrorState message={subs.error.message} onRetry={() => subs.refetch()} />}
      {subs.data && (
        <section className="jobs">
          {subs.data.map((sub) => <SubscriptionRow key={sub.id} sub={sub} />)}
          {subs.data.length === 0 && !adding && (
            <EmptyState
              icon="rss"
              title="No subscriptions yet"
              hint="Add a playlist or channel to keep it in sync — only new items get downloaded."
            />
          )}
        </section>
      )}
    </div>
  )
}
