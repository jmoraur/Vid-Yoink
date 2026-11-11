import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { DEFAULT_OPTIONS, type DownloadOptions, type Preset } from '../api/types'
import { OptionsForm } from '../components/options/OptionsForm'
import { summarize } from '../components/options/summarize'
import { ConfirmDelete } from '../components/ui/ConfirmDelete'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { Icon } from '../components/ui/Icon'
import { Skeleton } from '../components/ui/Skeleton'

function PresetEditor({
  preset,
  onDone,
}: {
  preset: Preset | null // null = creating new
  onDone: () => void
}) {
  const [name, setName] = useState(preset?.name ?? '')
  const [options, setOptions] = useState<DownloadOptions>(preset?.options ?? DEFAULT_OPTIONS)
  const queryClient = useQueryClient()
  const save = useMutation({
    mutationFn: () =>
      preset
        ? api.updatePreset(preset.id, name.trim(), options)
        : api.createPreset(name.trim(), options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['presets'] })
      onDone()
    },
  })

  return (
    <div className="preset-editor flat">
      <div className="row">
        <label className="grow">
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </label>
      </div>
      <OptionsForm value={options} onChange={setOptions} />
      <div className="row actions">
        <button disabled={!name.trim() || save.isPending} onClick={() => save.mutate()}>
          {preset ? 'Save changes' : 'Create preset'}
        </button>
        <button className="small" onClick={onDone}>
          Cancel
        </button>
        {save.isError && <span className="error">{save.error.message}</span>}
      </div>
    </div>
  )
}

export function Presets() {
  const [editing, setEditing] = useState<Preset | null | 'new'>(null)
  const queryClient = useQueryClient()
  const presets = useQuery({ queryKey: ['presets'], queryFn: api.listPresets })
  const remove = useMutation({
    mutationFn: (id: number) => api.deletePreset(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['presets'] }),
  })

  if (editing !== null) {
    return (
      <>
        <h2>{editing === 'new' ? 'New preset' : `Edit preset “${editing.name}”`}</h2>
        <PresetEditor preset={editing === 'new' ? null : editing} onDone={() => setEditing(null)} />
      </>
    )
  }

  return (
    <div>
      <div className="card-title-row">
        <h2>Presets</h2>
        <button className="small" onClick={() => setEditing('new')}>
          <Icon name="plus" size={14} /> New preset
        </button>
      </div>
      <p className="hint">
        Saved sets of download options. Pick one from the options panel on the Downloads
        page, or give one to a subscription.
      </p>
      {presets.isPending && <Skeleton lines={2} />}
      {presets.isError && (
        <ErrorState message={presets.error.message} onRetry={() => presets.refetch()} />
      )}
      {presets.data && (
        <section className="jobs">
          {presets.data.map((p) => (
            <div className="job" key={p.id}>
              <div className="job-main">
                <span className="job-title">{p.name}</span>
                <span className="job-actions">
                  <button className="small" onClick={() => setEditing(p)}>
                    Edit
                  </button>
                  <ConfirmDelete what={`preset ${p.name}`} onConfirm={() => remove.mutate(p.id)} />
                </span>
              </div>
              <p className="muted">{summarize(p.options)}</p>
            </div>
          ))}
          {presets.data.length === 0 && (
            <EmptyState
              icon="sliders"
              title="No presets yet"
              hint="Set up options on the Downloads page and save them, or create one here."
            />
          )}
        </section>
      )}
    </div>
  )
}
