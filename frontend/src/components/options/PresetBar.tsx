import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { DownloadOptions } from '../../api/types'

interface Props {
  options: DownloadOptions
  onLoad: (options: DownloadOptions) => void
}

export function PresetBar({ options, onLoad }: Props) {
  const [saving, setSaving] = useState(false)
  const [name, setName] = useState('')
  const queryClient = useQueryClient()
  const presets = useQuery({ queryKey: ['presets'], queryFn: api.listPresets })
  const save = useMutation({
    mutationFn: () => api.createPreset(name.trim(), options),
    onSuccess: () => {
      setSaving(false)
      setName('')
      queryClient.invalidateQueries({ queryKey: ['presets'] })
    },
  })

  return (
    <div className="preset-bar">
      <select
        value=""
        aria-label="Load preset"
        onChange={(e) => {
          const preset = presets.data?.find((p) => p.id === Number(e.target.value))
          if (preset) onLoad(preset.options)
        }}
      >
        <option value="" disabled>
          {presets.data?.length ? 'Load preset…' : 'No presets yet'}
        </option>
        {presets.data?.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      {saving ? (
        <>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Preset name"
            autoFocus
          />
          <button type="button" disabled={!name.trim() || save.isPending} onClick={() => save.mutate()}>
            Save
          </button>
          <button type="button" className="small" onClick={() => setSaving(false)}>
            Cancel
          </button>
        </>
      ) : (
        <button type="button" className="small" onClick={() => setSaving(true)}>
          Save as preset…
        </button>
      )}
      {save.isError && <span className="error">{save.error.message}</span>}
    </div>
  )
}
