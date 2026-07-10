import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { DEFAULT_OPTIONS, type DownloadOptions, type Preset } from '../api/types'
import { OptionsForm } from '../components/options/OptionsForm'

function summarize(o: DownloadOptions): string {
  const parts = [o.mode === 'audio' ? `audio (${o.audio_format})` : 'video']
  if (o.mode === 'video' && o.max_height) parts.push(`≤${o.max_height}p`)
  if (o.output_dir) parts.push(`→ ${o.output_dir}`)
  if (o.sponsorblock_remove.length) parts.push('sponsorblock')
  if (o.extra_args) parts.push(`extra: ${o.extra_args}`)
  return parts.join(' · ')
}

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
    <div className="preset-editor">
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
      <PresetEditor preset={editing === 'new' ? null : editing} onDone={() => setEditing(null)} />
    )
  }

  return (
    <div>
      <div className="page-actions">
        <button onClick={() => setEditing('new')}>New preset</button>
      </div>
      <section className="jobs">
        {presets.data?.map((p) => (
          <div className="job" key={p.id}>
            <div className="job-main">
              <span className="job-title">{p.name}</span>
              <button className="small" onClick={() => setEditing(p)}>
                Edit
              </button>
              <button className="small" onClick={() => remove.mutate(p.id)}>
                Delete
              </button>
            </div>
            <p className="muted">{summarize(p.options)}</p>
          </div>
        ))}
        {presets.data?.length === 0 && (
          <p className="muted">No presets yet. Configure options on the Download page and save them, or create one here.</p>
        )}
      </section>
    </div>
  )
}
